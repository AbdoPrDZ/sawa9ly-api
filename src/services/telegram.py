"""Linking a user to a Telegram chat, and receiving the messages that do it.

Nothing here decides *what* to notify a user about. It issues a link, recognises
the code when it comes back, and answers the person who sent it — which is the
whole of what binding needs. Sending anything else is a later concern, and
`send` is here only so a user can be told whether the binding worked.

The verification is the point of the module, so it is worth being explicit about
what a code proves. It proves two separate things at once:

- the sender can post in that chat, which is only true of someone who is in it;
- they are allowed to claim that account, because the code was issued for it.

Knowing a chat id proves neither, and a chat id is just a number Telegram hands
out — so without the code a user would be claiming a value they could read off a
screenshot. The code is what makes the binding mean something.
"""

import logging
import signal
import threading
import time

from src.config import Config
from src.db import session_scope
from src.models import TelegramBinding, TelegramBindingError, User
from src.utils import Telegram, TelegramError

logger = logging.getLogger(__name__)

#: `/start <code>`, which is how Telegram delivers a deep link's payload. The
#: command may be suffixed with the bot's own name, as in `/start@mybot CODE`.
START_COMMAND = "/start"

#: What `telegram test` sends. Plain text, no formatting: a notification has to
#: read correctly in whatever the client renders, and markdown that only half
#: applies is worse than none.
TEST_TEXT = (
  "Test notification from sawa9ly.\n"
  "\n"
  "This is a test, not a real event. If you can read this, your Telegram link "
  "is working and notifications will arrive here."
)


class _Interruptible:
  """A stop that works even while a long poll is blocking.

  A long poll is one blocking socket read, held open server-side for
  `TELEGRAM_POLL_TIMEOUT` seconds. On Windows a signal does not reach the Python
  interpreter until the blocking call returns, so Ctrl-C in a listener that is
  simply sitting there appears to do nothing for most of a minute — long enough
  that the reasonable conclusion is that it cannot be stopped at all. It can; it
  is just blocked, and the fix is not to be inside the blocking call.

  So the poll runs on a daemon thread and this waits for it in short slices from
  the main thread, which is back in Python bytecode often enough to be handed the
  signal within a fraction of a second.

  The abandoned poll is not a problem. The thread is a daemon, so the process
  still exits; the update it was waiting for is simply replayed on the next
  start, which this listener already handles, and the offset is only advanced for
  updates it actually saw.
  """

  #: How long to wait between checks for a stop. Short enough to feel immediate,
  #: long enough that an idle listener is not spinning.
  SLICE_SECONDS = 0.2

  def __init__(self):
    self.stop = threading.Event()
    self.previous = None
    self.previous_break = None
    # What the abandoned poll had managed so far. A listener stopped mid-poll
    # still handled a real number of updates, and reporting the count is the
    # difference between a summary and a shrug.
    self.progress = {}

  def arm(self):
    """Take over SIGINT so the first Ctrl-C stops rather than raising.

    Installed rather than merely caught because the exception cannot be raised
    while the main thread is blocked; the handler's whole job is to set a flag.

    SIGBREAK is taken too, so Ctrl-Break works as well. It is the one a terminal
    can deliver to a process running in its own group, which is how a listener
    started in the background gets stopped.
    """
    self.previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, self._on_interrupt)

    if hasattr(signal, "SIGBREAK"):
      self.previous_break = signal.getsignal(signal.SIGBREAK)
      signal.signal(signal.SIGBREAK, self._on_interrupt)

  def disarm(self):
    if self.previous is not None:
      signal.signal(signal.SIGINT, self.previous)
      self.previous = None

    if self.previous_break is not None:
      signal.signal(signal.SIGBREAK, self.previous_break)
      self.previous_break = None

  def requested(self):
    return self.stop.is_set()

  def _on_interrupt(self, signum, frame):
    # Logged here, from the handler, because the line is what tells a person
    # pressing Ctrl-C that it registered — the process may take a moment longer
    # to unwind and they would otherwise press it again.
    if not self.stop.is_set():
      logger.info("telegram: interrupt received, stopping")

    self.stop.set()

  def run(self, work):
    """Run `work` on a daemon thread until it finishes or a stop is requested.

    Returns what `work` returned, or None if it was asked to stop first.
    """
    box = {}

    def target():
      try:
        box['result'] = work()
      except BaseException as error:
        box['error'] = error

    thread = threading.Thread(target=target, daemon=True, name="telegram-poll")
    thread.start()

    while thread.is_alive() and not self.stop.is_set():
      thread.join(self.SLICE_SECONDS)

    if self.stop.is_set():
      return None

    if 'error' in box:
      raise box['error']

    return box.get('result')


class TelegramService:
  """Issuing binding links and acting on the messages that redeem them."""

  # --- issuing a link -------------------------------------------------

  @staticmethod
  def issue_link(db, username, bot=None):
    """A `t.me` link the named user can open to bind their chat.

    The code is carried in the link, so opening it needs no typing and cannot be
    mistyped. The plaintext is returned once and is not recoverable afterwards,
    which is why this is a link and not a code the user re-reads from a page.

    `bot` is injectable so this can be exercised without reaching Telegram. The
    caller does not pass one; only a test does.

    Returns:
        dict with `url`, `code` and `expires_at`. Widened rather than kept
        stable, so adding a field does not break a client that reads this.

    Raises:
        TelegramBindingError: If the user does not exist.
        TelegramError: If Telegram cannot be reached to name the bot.
    """
    user = TelegramService._user(db, username)
    code, row = TelegramBinding.issue(db, user.id)
    bot = bot or Telegram()

    return {
      'username': user.username,
      'url': bot.deep_link(code),
      'code': code,
      'expires_at': str(row.code_expires_at) if row.code_expires_at else None,
    }

  @staticmethod
  def binding(db, username):
    """The named user's binding, or an unbound-shaped dict if they have none.

    A missing row is not an error: not having linked a chat is the normal state
    for a user who never did.

    An **expired** code is reported as no code at all, and its deadline with it.
    The dashboard would otherwise say "waiting for you to open the link" about a
    code that can no longer be opened — which is worse than saying nothing, since
    it looks like something is coming. Deciding it here rather than in the client
    keeps the date arithmetic on one side of the wire and out of the browser.
    """
    user = TelegramService._user(db, username)
    row = TelegramBinding.for_user(db, user.id)

    if row is None:
      # Same keys as `as_dict`, with nothing set, so a caller renders one case
      # rather than a "no row" case and a "row with no chat" case.
      return {'user_id': user.id, 'bound': False, 'chat_id': None, 'chat_type': None,
              'chat_title': None, 'chat_username': None, 'code_pending': False,
              'code_expires_at': None, 'verified_at': None, 'created_at': None}

    described = row.as_dict()

    if row.code_hash is not None and row.code_expired():
      described['code_pending'] = False
      described['code_expires_at'] = None

    return described

  @staticmethod
  def unbind(db, username):
    """Forget this user's chat, so a new one can be linked.

    Returns True when there was something to forget. The row itself is kept, so
    issuing a code later has somewhere to land.
    """
    user = TelegramService._user(db, username)
    row = TelegramBinding.for_user(db, user.id)

    if row is None or not row.is_bound():
      return False

    row.unbind(db)

    return True

  @staticmethod
  def _user(db, username):
    """The named user, or a refusal saying there is no such account."""
    user = User.get(db, username)

    if user is None:
      raise TelegramBindingError(f"No user named {username!r}")

    return user

  # --- sending --------------------------------------------------------

  @staticmethod
  def send_to_user(db, username, text, bot=None):
    """Send a message to the chat this user linked.

    The one place a message goes to a user, so it is also the place that knows a
    user with no chat is not an error in Telegram but a gap here — and says what
    to do about it, rather than sending nothing and reporting success.

    Raises:
        TelegramBindingError: If no chat is linked, or the user does not exist.
        TelegramError: If Telegram refuses the message.
    """
    user = TelegramService._user(db, username)
    row = TelegramBinding.for_user(db, user.id)

    if row is None or not row.is_bound():
      raise TelegramBindingError(
        f"{user.username} has no Telegram chat linked, so there is nowhere to "
        f"send this. Link one from the dashboard's profile page, or open the link "
        f"it gives you."
      )

    (bot or Telegram()).send(row.chat_id, text)

    return {'username': user.username, 'chat_id': row.chat_id, 'sent': text}

  @staticmethod
  def send_test(db, username, bot=None):
    """Send a test notification, to check the link actually delivers.

    The only message this project sends on purpose. Real notifications are not
    wired up yet, so this is how a user — or an operator — finds out that a chat
    works, that the bot is not muted, and that the token is still valid, without
    having to wait for something worth being told about.
    """
    return TelegramService.send_to_user(db, username, TEST_TEXT, bot)

  # --- acting on a message --------------------------------------------

  @staticmethod
  def handle_update(db, update, bot):
    """Act on one Telegram update. Returns a short description of what happened.

    Every branch answers the sender, because a user who sends a code and hears
    nothing has no way to tell a broken bot from a typo. Failures are answered
    too — with the reason, not a traceback.
    """
    message = TelegramService._message_of(update)

    if message is None:
      # An update type this bot does not act on: a reaction, a member join. Not
      # an error, and not worth a reply, which would be noise in someone's chat.
      return None

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None:
      return None

    code = TelegramService._code_from(text)

    if code is None:
      if text.startswith(START_COMMAND):
        # `/start` with no payload: someone tapped the bot without a link, or
        # opened it by hand. Say what to do rather than staying silent.
        #
        # It asks for the *code*, not the link: a bot cannot do anything with a
        # t.me URL, and telling somebody to send one would be sending them in
        # circles. This is also the path that works when the deep link did not,
        # which is anyone on a desktop with no Telegram app installed.
        TelegramService._reply(
          bot, chat_id,
          "Send me your 10-character code to link this chat to your account. It "
          "is on your dashboard, under My profile → Telegram notifications.",
        )

        return 'no-code'

      return None

    try:
      return TelegramService._redeem(db, bot, code, chat_id)
    except TelegramBindingError as error:
      logger.info("telegram: refused a code from chat %s: %s", chat_id, error)
      TelegramService._reply(bot, chat_id, str(error))

      return 'refused'
    except TelegramError as error:
      # A failure reaching Telegram is not the user's fault and is not something
      # they can fix, so it is logged rather than sent to them as a dead end.
      logger.warning("telegram: could not answer chat %s: %s", chat_id, error)
      return 'unreachable'

  @staticmethod
  def _redeem(db, bot, code, chat_id):
    """Bind the chat the code came from, then confirm it."""
    row = TelegramBinding.verify(db, code)
    username = row.user.username

    # What Telegram says about the chat, not what the message claimed. This is
    # the read that decides whether the chat is one we will deliver to, so it
    # cannot come from a message.
    chat = bot.get_chat(chat_id)
    row.bind(db, chat)

    logger.info("telegram: linked %s to chat %s (%s)", username, chat_id,
                row.chat_type)

    TelegramService._reply(
      bot, chat_id,
      f"Linked to {username}. This chat will get your notifications.",
    )

    return f'bound:{username}'

  # --- pieces ---------------------------------------------------------

  @staticmethod
  def _message_of(update):
    """The message in an update, whichever field it arrived in.

    `message` is a chat message; `channel_post` is the same thing in a channel.
    Both are asked for in `allowed_updates`, and both are reduced here so
    nothing downstream has to know a channel is a different update type.
    """
    if not isinstance(update, dict):
      return None

    for field in ("message", "channel_post"):
      message = update.get(field)

      if isinstance(message, dict) and message.get("chat"):
        return message

    return None

  @staticmethod
  def _code_from(text):
    """The code in a message, or None if it does not hold one.

    Takes whatever `normalise_code` gives back rather than testing the text and
    then passing the original on: checking one form and hashing another is how a
    code that was accepted turns out to be unknown.
    """
    if not text:
      return None

    candidate = text

    if candidate.startswith(START_COMMAND):
      candidate = TelegramService._start_payload(candidate)

    # The payload first, then the whole message, for a code someone quoted
    # without the command.
    return (
      TelegramBinding.normalise_code(candidate)
      or TelegramBinding.normalise_code(text)
    )

  @staticmethod
  def _start_payload(command):
    """The payload out of a `/start` command.

    Telegram sends `/start CODE`, and `/start@BotName CODE` when the command was
    addressed to one bot by name — which is what a deep link produces when
    several bots share a username-free context. The bot name is attached to the
    command and is followed by a space, so it is the part before that space.

    `str.partition` is not usable for the split: with no `@` in the string it
    returns the whole of it as the *first* element, which is the opposite of what
    this wants.
    """
    rest = command[len(START_COMMAND):]

    if "@" in rest:
      _, _, after = rest.partition("@")
      _, space, tail = after.partition(" ")
      return tail if space else ""

    return rest.strip()

  @staticmethod
  def _reply(bot, chat_id, text):
    """Send a message, tolerating failure.

    A reply that cannot be sent must not take the listener down: the binding has
    already happened, and the next update is not going to repeat it.
    """
    try:
      bot.send(chat_id, text)
    except TelegramError as error:
      logger.warning("telegram: could not reply to chat %s: %s", chat_id, error)
      return False

    return True

  # --- the listener ---------------------------------------------------

  #: How many idle polls between "still here" lines. At the default 30s long poll
  #: that is one line every five minutes: often enough to prove the listener is
  #: alive and polling without burying the interesting lines, which is the whole
  #: reason this log exists.
  HEARTBEAT_POLLS = 10

  @staticmethod
  def listen(bot=None, max_updates=None):
    """Poll for updates and act on them until told to stop.

    `max_updates` stops after a number of updates, which is what makes this
    testable without Ctrl-C. The offset is held in memory and starts unset, so
    the first poll returns whatever Telegram still has — a code sent while this
    was not running is delivered rather than dropped.

    A restart replays up to 24 hours of updates, because Telegram keeps
    undelivered ones that long and the offset is not persisted. That is
    harmless here and cheaper than another piece of state: a code is single-use,
    so a replayed one is refused cleanly and the sender is told why.

    The polling runs on a thread so that Ctrl-C is answered promptly rather than
    after the current long poll returns; see `_Interruptible`.

    Returns:
        dict summarising what the run did.
    """
    bot = bot or Telegram()
    stop = _Interruptible()

    logger.info(
      "telegram: listening as %s, long poll %ss",
      Config.telegram_bot_name() or "(unnamed)", Config.TELEGRAM_POLL_TIMEOUT,
    )

    stop.arm()

    try:
      result = stop.run(
        lambda: TelegramService._poll(bot, max_updates, stop)
      )
    finally:
      stop.disarm()

    if result is None:
      # A stop, not a failure. The counts are whatever the abandoned poll had
      # reached, so the summary is still worth having.
      stopped = {
        'updates': stop.progress.get('updates', 0),
        'bound': stop.progress.get('bound', 0),
        'offset': stop.progress.get('offset'),
        'stopped': True,
      }

      logger.info("telegram: stopped after %s updates, %s linked",
                  stopped['updates'], stopped['bound'])

      return stopped

    logger.info(
      "telegram: finished, %s updates, %s linked", result['updates'],
      result['bound'],
    )

    return result

  @staticmethod
  def _poll(bot, max_updates, stop):
    """The polling loop itself, run on a thread by `listen`."""
    offset = None
    handled = 0
    bound = 0
    idle = 0

    while max_updates is None or handled < max_updates:
      if stop.requested():
        break

      try:
        updates = bot.get_updates(offset)
      except TelegramError as error:
        if error.conflict:
          # Another poller, or Telegram still draining this token's state.
          # Either way it clears, so wait rather than exiting or hammering.
          logger.warning("telegram: %s", error)
          TelegramService._pause()
          continue

        raise

      if not updates:
        # An idle poll is the normal case, and it is exactly the case that used
        # to leave the log empty — a listener that is working perfectly said
        # nothing at all, so "no logs" was indistinguishable from "not running".
        idle += 1

        if idle % TelegramService.HEARTBEAT_POLLS == 0:
          logger.info("telegram: still listening, %s updates so far", handled)

        continue

      # Updates arrived, so the next heartbeat is a fresh one.
      idle = 0

      for update in updates:
        update_id = update.get("update_id")

        # Confirm everything up to and including this one, so it is not sent
        # again. Telegram treats an update as delivered once a later offset
        # arrives, which is why the +1 matters.
        if update_id is not None:
          offset = update_id + 1

        handled += 1
        outcome = TelegramService._handle_one(update, bot)

        if outcome and outcome.startswith("bound:"):
          bound += 1

      # Published as it goes, so a stop that abandons this thread still reports
      # the counts rather than nothing.
      stop.progress.update(updates=handled, bound=bound, offset=offset)

    return {
      'updates': handled,
      'bound': bound,
      'offset': offset,
    }

  @staticmethod
  def _pause():
    """Wait out a 409.

    A conflict is always transient — a second poller, or Telegram still draining
    this token's state after one stopped — so this sleeps rather than exiting.
    Exiting would make a bot that was restarted a minute too early stay dead.
    """
    logger.info(
      "telegram: waiting %ss before polling again", Config.TELEGRAM_CONFLICT_BACKOFF
    )
    time.sleep(Config.TELEGRAM_CONFLICT_BACKOFF)

  @staticmethod
  def _handle_one(update, bot):
    """Act on one update in its own session, and report the outcome.

    A database session per update rather than one for the whole run: a listener
    is long-lived, and a session held across every poll would carry whatever the
    last update loaded for as long as the process lives.
    """
    try:
      with session_scope() as db:
        return TelegramService.handle_update(db, update, bot)
    except TelegramBindingError as error:
      # Already answered to the sender inside handle_update; this is the
      # database refusing something the model thought was fine.
      logger.warning("telegram: %s", error)
      return 'refused'
