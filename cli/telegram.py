"""CLI: the Telegram listener, and a way to check a link works.

`listen` and `test`, and nothing else. Issuing a link, reading the current binding
and unbinding are all the user's own business and live in the dashboard, because
they are things a person does once rather than an operation a script repeats. The
listener is the exception: it is a process rather than an action, so it needs a
command to live in, exactly as `cron listen` does.

`test` is here for the same reason. Real notifications are not wired up yet, so
without it there is no way to find out whether a linked chat works except waiting
for something worth being told about.
"""

import sys
from pathlib import Path

from src.config import Config
from src.services import TelegramService
from src.services.cron import Cron
from src.utils import TelegramError

#: The listener's own lock file. Separate from the queue's: a running queue and a
#: running bot are two different things, and neither should refuse to start
#: because the other is going.
LOCK_NAME = "telegram.lock"


class TelegramCli:
  """`telegram` - receive the messages that link an account to a chat."""

  @staticmethod
  def register(commands):
    telegram = commands.add_parser('telegram', help="the Telegram bot")
    actions = telegram.add_subparsers(dest='action', required=True)

    listen = actions.add_parser(
      'listen',
      help="poll Telegram for binding codes, forever",
    )
    listen.add_argument(
      '--max-updates', type=int, default=None,
      help="stop after this many updates (for testing)",
    )

    test = actions.add_parser(
      'test',
      help="send a test notification to a linked chat",
    )
    test.add_argument(
      '--user', default=None,
      help="whose chat to send to; defaults to the super admin",
    )

  @staticmethod
  def dispatch(args):
    if args.action == 'listen':
      return TelegramCli._listen(args)

    if args.action == 'test':
      return TelegramCli._test(args)

    raise SystemExit(f"error: unknown telegram action {args.action!r}")

  @staticmethod
  def _test(args):
    """Send a test message, and report where it went.

    Exits non-zero when it cannot, so this is usable as a check in a script:
    `telegram test && echo delivered` means what it looks like.
    """
    from cli.base import Cli

    with Cli.db() as db:
      return TelegramService.send_test(db, Cli.username(args.user))

  @staticmethod
  def _listen(args):
    if not Config.telegram_configured():
      raise TelegramError(
        f"No bot token, so there is nothing to listen with. Set "
        f"{Config.TELEGRAM_BOT_TOKEN_VAR} in .env, from the token @BotFather "
        f"gave you when you created the bot."
      )

    # Taken before the first poll, because one poller per token is Telegram's
    # rule. A second one is not refused politely either: it is answered with a
    # 409 on every poll, forever, and a listener that can only fail in a way that
    # looks like a network problem is worse than one that says why it stopped.
    lock = Cron._Lock(
      Path(Config.DATA_DIR) / LOCK_NAME,
      # 0: never take a stale lock over. A listener is started by hand, so a
      # leftover file is an accident to be told about, not a pass that is still
      # working — and unlike a queue pass, waiting 15 minutes for it is not a
      # reasonable answer to "it does nothing".
      0,
      "A Telegram listener is already running (lock: {path}). Only one may poll "
      "a bot token. Stop the other first, or delete that file if you are sure "
      "none is running.",
    )

    with lock:
      try:
        return TelegramService.listen(max_updates=args.max_updates)
      except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr, flush=True)

        return {'stopped': True}
