"""A client for the Telegram Bot API.

Telegram is reached over plain HTTPS with `requests`, which this project already
depends on for the site, so the integration adds no package.

**The token never leaves this module.** It sits in the URL path of every Bot API
call, the way the API is designed, and that makes it a standing leak risk:

- `requests` and `urllib3` quote the full URL in their error messages, so an
  exception that escapes with the URL attached has written the token into a log,
  a traceback or a cron summary.
- The project's `SecretFilter` does not save us, and cannot. It redacts the value
  after a `key=value` or `key: value` pair in the rendered line, and a token in a
  URL has neither - it sits after `/bot`, with nothing in front of it naming it as
  a secret. So the field-name filter has nothing to match and this module's
  `_redact` is the only thing standing between a token and a log file.

So the rule here is that the token lives in exactly one private attribute, URLs
are built from a base plus a method name, and every error that leaves this module
has the token stripped from it. Nothing else in the project builds a Bot API URL.

Receiving updates is done by long polling, not a webhook, so this needs no public
address, no TLS certificate and no domain — it dials Telegram and Telegram never
dials back. Telegram holds undelivered updates for up to 24 hours, so a bot that
was not listening when a message was sent still gets it on the next poll.
"""

import logging

import requests

from src.config import Config

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"

#: Deep link to a bot's private chat with a payload. Opening it delivers
#: `/start <payload>` to the bot, so the code is carried rather than typed.
DEEP_LINK = "https://t.me/{username}?start={payload}"

#: How long to wait for a response that includes the long-poll timeout. Without
#: this, `requests` times out first and every poll looks like a network failure.
_HTTP_TIMEOUT_SLACK = 15

#: Update types this bot acts on. Asking for only these keeps the payload small:
#: a busy chat would otherwise deliver reactions and member events we ignore.
#: `channel_post` is here so a private channel works as well as a private chat.
WANTED_UPDATES = ["message", "channel_post"]


class TelegramError(Exception):
  """A Bot API call could not be completed.

  Carries `conflict` so a caller can tell "another poller holds this token" from
  every other failure, which are not the same thing and are not retried alike.
  """

  def __init__(self, message, conflict=False, code=None):
    super().__init__(message)
    self.conflict = conflict
    self.code = code


class Telegram:
  """One bot, by token.

  Not a shared singleton: the token identifies the bot, and a caller that has
  one has already decided which. Building it is cheap and it holds no session.
  """

  def __init__(self, token=None, timeout=None):
    token = token or Config.telegram_token()

    if not token:
      raise TelegramError(
        f"No bot token. Set {Config.TELEGRAM_BOT_TOKEN_VAR} in .env, from the "
        "token @BotFather gave you when you created the bot."
      )

    self._token = token
    self._timeout = timeout or Config.TELEGRAM_POLL_TIMEOUT

  # --- calls ----------------------------------------------------------

  def get_me(self):
    """The bot's own account: its id and @username.

    The authoritative source for the username, so a deep link cannot name a bot
    the token does not belong to.
    """
    return self._call("getMe")

  def get_chat(self, chat_id):
    """What Telegram knows about a chat: its `type`, `title` and `username`.

    Read before binding rather than trusted from the message, because the type is
    what decides whether a chat is one we will deliver to.
    """
    return self._call("getChat", {"chat_id": chat_id})

  def get_updates(self, offset=None):
    """The next batch of updates, waiting for them if there are none.

    `offset` confirms every update below it as delivered, so the caller passes
    the highest id it has seen plus one. Omitting it returns the earliest
    unconfirmed update, which is what makes a restart pick up whatever was
    queued while this was not running.
    """
    params = {
      "timeout": self._timeout,
      "allowed_updates": WANTED_UPDATES,
    }

    if offset is not None:
      params["offset"] = offset

    return self._call("getUpdates", params)

  def send(self, chat_id, text):
    """Send a message to a chat. Returns the sent message."""
    return self._call("sendMessage", {"chat_id": chat_id, "text": text})

  # --- transport ------------------------------------------------------

  def deep_link(self, payload):
    """The `t.me` link that delivers `payload` to this bot's private chat.

    Uses `getMe` for the username rather than the environment, so the link cannot
    disagree with the token. The environment name is only a fallback, for when
    Telegram cannot be reached to ask.
    """
    username = self.username()

    return DEEP_LINK.format(username=username, payload=payload)

  def username(self):
    """This bot's @username, without the `@`."""
    try:
      me = self.get_me()
    except TelegramError as error:
      fallback = Config.telegram_bot_name()

      if not fallback:
        raise TelegramError(
          f"Could not read the bot's name from Telegram ({error}). Set "
          f"{Config.TELEGRAM_BOT_NAME_VAR} as a fallback, or check the network."
        ) from None

      logger.warning("falling back to %s for the bot name: %s", Config.TELEGRAM_BOT_NAME_VAR, error)

      return fallback

    return (me.get("username") or "").lstrip("@") or None

  def _call(self, method, params=None):
    """POST to a Bot API method and return its `result`.

    The token appears in the URL and nowhere else, and the URL is never allowed
    into an exception or a log line.
    """
    url = f"{API_ROOT}/bot{self._token}/{method}"
    body = {k: v for k, v in (params or {}).items() if v is not None}

    # The long poll is held open server-side for `timeout` seconds, so the read
    # timeout has to be longer than that or every empty poll looks like a failure.
    read_timeout = self._timeout + _HTTP_TIMEOUT_SLACK

    try:
      response = requests.post(url, json=body, timeout=read_timeout)
    except requests.RequestException as error:
      # The request's own repr carries the URL, so it is stripped before the
      # message is allowed out of this function.
      raise TelegramError(
        f"Telegram did not answer {method}: {self._redact(str(error))}"
      ) from None

    return self._result(method, response)

  def _result(self, method, response):
    """Unwrap the Bot API envelope, or raise with the token removed."""
    try:
      payload = response.json()
    except ValueError:
      raise TelegramError(
        f"Telegram answered {method} with {response.status_code} and a body that "
        f"is not JSON: {self._redact(response.text)[:200]}"
      ) from None

    if payload.get("ok"):
      return payload.get("result")

    description = payload.get("description") or "no reason given"
    code = payload.get("error_code")

    if code == 409:
      # Telegram's own wording is that only one poller may hold a token. It is
      # transient — the token keeps some poll state for a while after a poller
      # exits — so this is a distinct case rather than a generic failure.
      raise TelegramError(
        f"Another poller is using this bot token ({self._redact(description)}). "
        "Only one `telegram listen` may run at a time; if you are sure none is, "
        "wait a minute and retry, because Telegram keeps poll state briefly "
        "after a poller stops.",
        conflict=True,
        code=code,
      )

    raise TelegramError(
      f"Telegram refused {method} ({code}): {self._redact(description)}",
      code=code,
    )

  def _redact(self, text):
    """The text with this bot's token replaced, if it appears at all.

    The backstop. Everything above is written so the token never gets this far;
      this exists because the one place we do not control — a third party's
      error message — is exactly the place it does.
    """
    if not text:
      return text

    return text.replace(self._token, "[redacted]")

  def __repr__(self):
    # A repr reaches logs and tracebacks. It cannot carry the token.
    return "<Telegram bot>"
