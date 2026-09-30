# Telegram notifications

A user can link a Telegram chat to their account and be reached there. Nothing
else in the project depends on it: with no `TELEGRAM_BOT_TOKEN` set, the whole
feature is simply off.

## Linking a chat

The link is on the user's own **My profile** page, and it is shown once.

1. The dashboard issues a **single-use code**, 10 characters, valid for 15
   minutes, stored only as a SHA-256 digest — so the code cannot be read back out
   of the database, only reissued.
2. It is handed over as a `t.me` link carrying that code. Opening the link
   delivers `/start <code>` to the bot, so there is nothing to type and nothing to
   mistype.
3. `python main.py telegram listen` receives it, checks the code, and stores the
   chat id against that user.
4. The bot replies, so a user who sent the code and heard nothing knows something
   went wrong.

What the code proves is two things at once: that the sender can post in that chat,
and that they were allowed to claim that account. A chat id on its own proves
neither — it is just a number Telegram hands out, readable off a screenshot.

**On the page, press "Open in Web" — not "Start Bot".** The link's page has two
buttons and the obvious one is the one that fails. "Start Bot" hands off to the
Telegram app through the `tg://` scheme; on a computer with no app installed
Chrome reports *"Failed to launch 'tg://resolve?…' because the scheme does not
have a registered handler"* and the button does nothing at all, silently.
"Open in Web" carries the same code in a `tgaddr` fragment and works with no app
installed. The code is on the same page too, and the bot takes it as a message
from the app or from **web.telegram.org** — bare, in backticks, in lower case, or
after `/start`. A sentence containing a code is refused on purpose, so ordinary
chatter cannot bind a chat by accident.

A **private chat with the bot** needs no setup at all. A **private channel** works
too, but the bot must be added as an admin of it, and because a channel is
broadcast-only you must be an admin as well to post the code. A **group is
refused** — it is shared with people who are not this user, so `chat_type` is
checked in the database, not just in the UI.

Issuing a new link does not unbind an existing chat, so a code that is never used
costs the user nothing. One chat belongs to one account, enforced by a
`UNIQUE(chat_id)`, so two users cannot claim the same channel.

## The listener

```bash
python main.py telegram listen                    # forever
python main.py telegram listen --max-updates 5    # stop after 5, for testing
```

It **polls** rather than taking a webhook, which is why it needs no public
address, no TLS certificate and no domain: it dials Telegram, and Telegram never
dials back. ngrok, a DDNS name and a real domain are all unnecessary here.

Two consequences worth knowing:

- **The bot is deaf while the listener is stopped.** Telegram holds undelivered
  updates for up to 24 hours, so a code sent in the meantime is delivered when it
  next starts — but nothing arrives while it is down.
- **Only one listener may run at a time.** Telegram allows one `getUpdates` per
  token and answers a second poller with a 409 on *every* poll, so a lock file
  refuses the second process up front instead. A 409 is also treated as transient
  and backed off, because Telegram keeps a token's poll state for a minute or so
  after a poller exits — so a listener restarted too quickly recovers by itself.

The offset is held in memory and starts unset, which is what lets a restart pick up
whatever was queued. A restart therefore replays up to 24 hours of updates, which
is harmless: codes are single-use, so a replayed one is refused cleanly and the
sender is told why.

## Checking a link works

```bash
python main.py telegram test --user alice      # send a test message
```

This sends a message you asked for, so it is also the quickest way to find out
that a chat works — that the bot is not muted, and that the token is still valid —
without waiting for something worth being told about.

It exits non-zero when it cannot send, so it works as a check in a script:
`telegram test --user alice && echo delivered` means what it looks like. A user
with no linked chat is an `error:` naming the dashboard page that fixes it, and a
chat the user has since blocked comes back as Telegram's own 403 reason.

## What gets a notification

One kind of event, for now: **a watched product changed**. When the queue fetches
a product and finds that its stock or its price is different from what is stored,
everyone watching that product is told. See
[`.agents/context/domains/notifications.md`](../../.agents/context/domains/notifications.md)
for how the record and its delivery are kept.

## The token

The Bot API puts the token in the URL of every call, so `requests` and `urllib3`
quote it in their error messages. `src/utils/telegram.py` keeps it in one private
attribute, strips it from every error that leaves the module, and has a `__repr__`
that cannot leak it. The project's log filter does **not** cover this: it redacts a
record only when the message contains a word like `token` or `secret`, and a real
token contains neither.
