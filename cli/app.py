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
from cli.product import ProductCli
from cli.serve import ServeCli
from cli.track import TrackCli
from src.services import CronError, OrderError, TrackingError
from src.utils.livewire import LivewireError

# Refusals the CLI reports as `error: ...` with a non-zero exit, rather than
# treating them as a crash.
EXPECTED_ERRORS = (LivewireError, OrderError, TrackingError, CronError)


class App:
  """Builds the parser and runs the selected command."""

  GROUPS = (
    ProductCli,
    CatalogueCli,
    ClientCli,
    OrderCli,
    AccountCli,
    TrackCli,
    CronCli,
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
      'ProductCli': {'cart', 'login', 'product', 'cart-add', 'cart-remove',
                     'cart-set-quantity', 'cart-set-price', 'cart-remove-item', 'checkout'},
      'CatalogueCli': {'catalogue'},
      'ClientCli': {'client'},
      'OrderCli': {'order'},
      'AccountCli': {'user', 'apikey'},
      'TrackCli': {'track'},
      'CronCli': {'cron'},
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
