# Telegram

A user can link one Telegram chat to their account, and be reached there. Nothing
else in the project depends on it: with no `TELEGRAM_BOT_TOKEN` set, the whole
feature is off and the rest of the app is unaffected.

| | |
| --- | --- |
| Entity | `TelegramBinding`, `telegram_bindings` |
| Transport | `src/utils/telegram.py` — the Bot API over `requests` |
| Service | `src/services/telegram.py` — links, and acting on messages |
| Routes | `/api/v1/telegram`, `GET` / `POST /link` / `DELETE` |
| Process | `python main.py telegram listen` |
| Config | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_NAME` (fallback only) |

## The verification, and why a code

Linking a chat means proving the person asking owns it. A chat id on its own does
not: Telegram hands those out, and anyone can read one off a screenshot. So the
binding is made by a **single-use code**.

What the code proves is two separate things at once — the sender can post in that
chat, and they were allowed to claim that account. Either alone would be
insufficient, and a chat id is worth nothing without the second.

The code is 10 characters from an alphabet with no `0`/`O`, `1`/`I` or `l`, valid
for 15 minutes, and stored only as a SHA-256 digest — so it cannot be read back
out of the database, only reissued. It travels as a `t.me` deep link rather than
being typed, because a link cannot be mistyped and does not get shoulder-surfed
in a group chat.

**The deep link needs the right button, and the code needs no button at all.**
`t.me` hands off through the `tg://` scheme, and a machine with no app installed
reports *"scheme does not have a registered handler"* and does nothing, silently.
The page has **two** buttons and the obvious one is the one that fails:

| Button | Href | Works with no app? |
| --- | --- | --- |
| **Start Bot** | `tg://resolve?domain=…&start=…` | no |
| **Open in Web** | `https://web.telegram.org/a/#?tgaddr=tg%3A%2F%2Fresolve%3F…%26start%3D…` | yes |

Both carry the same code; the web one smuggles it through as a `tgaddr` fragment.
**Any instruction for a user must name "Open in Web"** — "open this link" sends
them to the page and to the button that does nothing, and they cannot tell the
difference between a dead button and a broken one.

The code is on the same page, and the bot takes it as a message from the app or
from web.telegram.org, so it is offered alongside for the same reason. **Never
make the link the only way in.**

`normalise_code` returns the cleaned code or None, and `hash_code` normalises
too. That is deliberate: an earlier version had the matcher strip quotes and
backticks to *decide* a message held a code, then handed back the original text,
which was then hashed with the backticks still on it. A user copying from a
backticked page was told their code was unknown while looking at it. **The thing
that decides and the thing that hands the code on must be the same call.**

A sentence *containing* a code is refused, because stripping the words out would
leave a 10-character match for the wrong reason. Incidental text must not be able
to bind a chat.

## One row carries both halves

`telegram_bindings` is one row per user, and the row moves between two states:

| | `chat_id` | `code_hash` |
| --- | --- | --- |
| issued | null | set |
| verified | set | null |

So issuing a code and redeeming one are the same row, there is never more than one
outstanding code per user, and **nothing needs cleaning up**. Issuing a code does
*not* clear an existing `chat_id`, so a code that is never used costs the user
nothing — and re-binding works, because a successful verification overwrites.

`UNIQUE(chat_id)` is what makes one chat belong to one account. It is a database
constraint rather than a check in the service, so it holds even if something
reaches the table another way.

## Groups are refused, in the database

`DELIVERABLE_CHAT_TYPES` is `private` and `channel`; a `group` or `supergroup` is
refused. A group is shared with people who are not this user, and a notification
meant for one account arriving in everybody's group chat is not that user's to
send. `bind()` checks `getChat`'s own `type` — read from Telegram, never taken
from the message — and the table stores it so the rule is inspectable.

The cost is that a **private channel needs the bot added as an admin**, and
because a channel is broadcast-only the user must be an admin too in order to post
the code. A private chat with the bot needs no setup at all.

## Polling, not a webhook

Updates are received by long polling, so this needs **no public address, no
certificate and no domain**: the listener dials Telegram, and Telegram never
dials back. ngrok, DDNS and a real domain are all unnecessary for it.

Two consequences:

- The bot is deaf while the listener is stopped. Telegram keeps undelivered
  updates for **24 hours**, so a code sent meanwhile arrives when it next starts.
- **Only one poller per token.** Telegram allows one `getUpdates` and answers a
  second with a 409 on *every* poll, which reads like a network fault rather than
  like what it is — so `data/telegram.lock` refuses the second process up front,
  reusing `Cron._Lock` with a staleness of 0 so a leftover file is reported rather
  than waited out. A 409 that does arrive is treated as transient and backed off,
  because Telegram keeps a token's poll state for a minute or so after a poller
  exits and a restart too early recovers by itself.

The offset is **not persisted**: it is held in memory and starts unset, so the
first poll returns whatever is queued. A restart therefore replays up to 24 hours
of updates, which is harmless — codes are single-use, so a replayed one is
refused cleanly and the sender is told why.

## The token is a standing leak risk

The Bot API puts the token in the URL of every call, and `requests`/`urllib3`
quote the full URL in their error messages. **The project's `SecretFilter` does
not cover this**: it redacts the value after a `key=value` or `key: value` pair
in the rendered line, and a token in a URL has neither — it sits after `/bot`,
with nothing naming it as a secret, so the field-name filter has nothing to match.
This module's `_redact` is the only thing standing between a token and a log file.

So `src/utils/telegram.py` treats the token as the file's whole reason to exist:
it lives in one private attribute, URLs are built from a base plus a method name,
`_redact` strips it from everything that leaves the module, and `__repr__` cannot
leak it. Nothing outside that file builds a Bot API URL.

## Sending

`TelegramService.send_to_user` is the **only** place a message goes to a user, and
it is the one that knows a user with no linked chat is a gap here rather than a
fault in Telegram — so it says which dashboard page fixes it.

Exactly one message is sent on purpose today: `telegram test` sends `TEST_TEXT` to
check that a link delivers. Real notifications are **not** wired up; the
order-state and price-change events that would drive them are noted in
`tracking.md` and `domains/orders.md` as the obvious callers. The
"what to notify about" decision was deferred, so the trigger is not here.

`TelegramBindingError` and `TelegramError` are both in the CLI's
`EXPECTED_ERRORS`, so "no chat is linked" and "the user blocked the bot" come out
as `error: ...` with a non-zero exit rather than a traceback — which is what makes
`telegram test && echo delivered` mean what it looks like.

## Nobody links somebody else's chat

`/api/v1/telegram` acts only on the caller, and there is deliberately **no admin
route that issues a link for another user**. A link is the right to send messages
into a chat, so an admin who could mint one could claim a user's notifications.
A super can *see* which chat a user linked (`telegram_chat_id` in
`AdminUserOut`) for support, which is the fact and not the capability.
