"""CLI: watching products for changes.

Managing *what* is watched lives here. *When* it is checked is the `cron`
command, in `cli/cron.py`.
"""

from src.models import TargetModel


class TrackCli:
  """`track` — subscribe to a product's changes."""

  @staticmethod
  def register(commands):
    track = commands.add_parser('track', help="watch products for changes")
    actions = track.add_subparsers(dest='action', required=True)

    watch = actions.add_parser('watch', help="start watching a saved product")
    watch.add_argument('product_id')
    watch.add_argument('--user', help="who is watching; defaults to the super admin")

    unwatch = actions.add_parser('unwatch', help="stop watching a product")
    unwatch.add_argument('product_id')
    unwatch.add_argument('--user', help="who is watching; defaults to the super admin")

    listing = actions.add_parser('list', help="list what a user is watching")
    listing.add_argument('--user', help="whose watches to list; defaults to the super admin")
    listing.add_argument('--model', default=None, choices=list(TargetModel.ALL),
                         help="only one kind of target")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.services import Tracking

    with Cli.db() as db:
      if args.action == 'watch':
        tracker, created = Tracking.watch_product(db, args.product_id, args.user)
        row = tracker.as_dict()
        row['created'] = created

        return row

      if args.action == 'unwatch':
        if not Tracking.unwatch_product(db, args.product_id, args.user):
          raise SystemExit(
            f"error: '{args.user}' is not watching product {args.product_id}"
          )

        return {'unwatched': int(args.product_id), 'user': args.user}

      if args.action == 'list':
        return {
          'user': args.user,
          'watching': Tracking.for_user(db, args.user, args.model),
        }
