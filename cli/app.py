"""Command line application.

Each command group lives in its own module and contributes both the
subparsers it accepts and a `dispatch` that runs them, so adding a service
means adding a file rather than growing one.

Every invocation is recorded in `sawa9ly-cli.log`: which command, for which
account, and whether it finished or was refused. These commands create API keys,
place orders and edit the account table, so the trail of who ran what is worth
keeping — and it is the only record of a command once its output has scrolled
away or been piped somewhere. Only the command and its action are recorded, never
the full argument list, because an argument is exactly where a password or a
cookie would appear.
"""

import argparse
import logging
import sys
import time

from cli.account import AccountCli
from cli.catalogue import CatalogueCli
from cli.client import ClientCli
from cli.cron import CronCli
from cli.mcp import McpCli
from cli.order import OrderCli
from cli.output import Output
from cli.page import PageCli
from cli.product import ProductCli
from cli.router import RouterCli
from cli.serve import ServeCli
from cli.shipping import ShippingCli
from cli.telegram import TelegramCli
from cli.track import TrackCli
from src.models import ReferenceDataMissing, TelegramBindingError
from src.services import (
  AccountsError,
  CronError,
  OrderError,
  PageError,
  SeedMissing,
  TrackingError,
)
from src.utils.livewire import LivewireError
from src.utils.telegram import TelegramError

logger = logging.getLogger(__name__)

# Refusals the CLI reports as `error: ...` with a non-zero exit, rather than
# treating them as a crash.
#
# AccountsError is here because assembling the app is a refusal with a perfectly
# good message: a command that reaches `create_app` — `serve`, and `router` via
# its route table — hits the super-account guard on a checkout that has neither a
# super nor the environment to make one, and that is a setup step to report, not
# a crash to dump a traceback over.
#
# TelegramError is here for the same reason: a missing bot token is a setup step,
# and `telegram listen` says which variable to set. TelegramBindingError is its
# sibling: "no chat is linked" and "that code is not one we issued" are answers,
# not faults.
#
# ReferenceDataMissing and SeedMissing are setup steps for the same reason: the
# delivery reference data is seeded rather than scraped, so an unseeded database
# or a distribution without the file is a missing file with a known command, not
# a fault.
EXPECTED_ERRORS = (
  LivewireError, OrderError, PageError, TrackingError, CronError, AccountsError,
  TelegramError, TelegramBindingError, ReferenceDataMissing, SeedMissing,
)


class App:
  """Builds the parser and runs the selected command."""

  GROUPS = (
    ProductCli,
    CatalogueCli,
    ShippingCli,
    ClientCli,
    OrderCli,
    PageCli,
    AccountCli,
    TrackCli,
    CronCli,
    TelegramCli,
    RouterCli,
    ServeCli,
    McpCli,
  )

  @staticmethod
  def build_parser():
    parser = argparse.ArgumentParser(prog="sawa9ly", description="sawa9ly client")
    parser.add_argument('--json', action='store_true',
                        help="print raw JSON instead of a table")
    commands = parser.add_subparsers(dest='command', required=True)

    for group in App.GROUPS:
      group.register(commands)

    return parser

  @staticmethod
  def run(args):
    from cli.base import Cli

    # `--user` is optional and falls back to the super admin. Resolved once, here,
    # so every group below receives a concrete account name and none of them has to
    # know the fallback exists. Only commands that declare `--user` have the
    # attribute; `user add <name>` and friends use `username` and are left alone.
    if hasattr(args, 'user') and not args.user:
      args.user = Cli.super_username()

    for group in App.GROUPS:
      dispatch = getattr(group, 'dispatch', None)

      if dispatch is None:
        continue

      if not App._handles(group, args.command):
        continue

      return dispatch(args)

    raise SystemExit(f"unknown command: {args.command}")

  @staticmethod
  def _handles(group, command):
    """Whether this group owns the given command name."""
    names = {
      'ProductCli': {'cart', 'login', 'product', 'checkout'},
      'CatalogueCli': {'catalogue'},
      'ShippingCli': {'shipping'},
      'ClientCli': {'client'},
      'OrderCli': {'order'},
      'PageCli': {'page'},
      'AccountCli': {'user', 'apikey'},
      'TrackCli': {'track'},
      'CronCli': {'cron'},
      'TelegramCli': {'telegram'},
      'RouterCli': {'router'},
      'ServeCli': {'serve'},
      'McpCli': {'mcp'},
    }
    return command in names.get(group.__name__, set())

  @staticmethod
  def _describe(args):
    """`command action`, for the log. Never the arguments themselves.

    The sub-action is the one positional a command takes, and it is a verb like
    `add` or `show`. The arguments after it are the values a person typed, which
    is where a password, a token or a session cookie would be, so they stay out
    of the log entirely rather than being filtered on the way through.
    """
    action = getattr(args, "action", None)

    return f"{args.command} {action}" if action else str(args.command)

  @staticmethod
  def _utf8_stdout():
    """Let a command print Arabic and French names without dying.

    A Windows console still defaults to cp1252, and `print` raises
    `UnicodeEncodeError` rather than substituting anything — so `catalogue list`
    died on the first Arabic product title, and any command that renders a wilaya
    or a commune name died the same way. Reconfigured here, at the one place that
    writes to the terminal, rather than in every command that happens to have
    something to say.

    A console that genuinely cannot render UTF-8 shows mojibake instead of
    crashing, which is the better of the two: the data still arrives. Output
    redirected to a file or a pipe is already UTF-8 and is left alone.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)

    if reconfigure is None:
      return

    try:
      if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
        reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
      # A stream that cannot be reconfigured — replaced, or already closed. The
      # print below will raise whatever it would have raised anyway.
      pass

  @staticmethod
  def main():
    args = App.build_parser().parse_args()

    # Before the command runs, not after: the interesting failures happen while a
    # long-running command is working, and a queue or a bot that logged nothing
    # until it exited would leave no trace of a pass that went wrong.
    from src.logging_setup import Logging

    Logging.configure()

    described = App._describe(args)
    account = getattr(args, "user", None)
    who = f" as {account}" if account else ""
    started = time.perf_counter()

    logger.info("running %s%s", described, who)

    try:
      result = App.run(args)
    except EXPECTED_ERRORS as error:
      # A refusal, not a crash, so it is a warning: the operator sees the reason
      # and the exit code, and the log shows the same thing happened here.
      logger.warning("%s%s refused after %.0fms: %s",
                     described, who, (time.perf_counter() - started) * 1000, error)
      raise SystemExit(f"error: {error}")

    logger.info("%s%s done in %.0fms", described, who,
                (time.perf_counter() - started) * 1000)

    if result is not None:
      App._utf8_stdout()
      print(Output.render(result, as_json=args.json))
