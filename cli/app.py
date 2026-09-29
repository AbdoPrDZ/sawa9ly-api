"""Command line application.

Each command group lives in its own module and contributes both the
subparsers it accepts and a `dispatch` that runs them, so adding a service
means adding a file rather than growing one.
"""

import argparse

from cli.account import AccountCli
from cli.catalogue import CatalogueCli
from cli.client import ClientCli
from cli.cron import CronCli
from cli.order import OrderCli
from cli.output import Output
from cli.page import PageCli
from cli.product import ProductCli
from cli.router import RouterCli
from cli.serve import ServeCli
from cli.track import TrackCli
from src.services import (
  AccountsError,
  CronError,
  OrderError,
  PageError,
  TrackingError,
)
from src.utils.livewire import LivewireError

# Refusals the CLI reports as `error: ...` with a non-zero exit, rather than
# treating them as a crash.
#
# AccountsError is here because assembling the app is a refusal with a perfectly
# good message: a command that reaches `create_app` — `serve`, and `router` via
# its route table — hits the super-account guard on a checkout that has neither a
# super nor the environment to make one, and that is a setup step to report, not
# a crash to dump a traceback over.
EXPECTED_ERRORS = (
  LivewireError, OrderError, PageError, TrackingError, CronError, AccountsError,
)


class App:
  """Builds the parser and runs the selected command."""

  GROUPS = (
    ProductCli,
    CatalogueCli,
    ClientCli,
    OrderCli,
    PageCli,
    AccountCli,
    TrackCli,
    CronCli,
    RouterCli,
    ServeCli,
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
      'ClientCli': {'client'},
      'OrderCli': {'order'},
      'PageCli': {'page'},
      'AccountCli': {'user', 'apikey'},
      'TrackCli': {'track'},
      'CronCli': {'cron'},
      'RouterCli': {'router'},
      'ServeCli': {'serve'},
    }
    return command in names.get(group.__name__, set())

  @staticmethod
  def main():
    args = App.build_parser().parse_args()

    try:
      result = App.run(args)
    except EXPECTED_ERRORS as error:
      raise SystemExit(f"error: {error}")

    if result is not None:
      print(Output.render(result, as_json=args.json))
