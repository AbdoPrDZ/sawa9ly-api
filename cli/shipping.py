"""CLI: the site's delivery reference data and its prices per wilaya."""

from src.services import Seed, Shipping


class ShippingCli:
  """`shipping` — the wilayas, their communes, and what delivery costs.

  The prices are the site's alone, one list for everybody, so nothing here is
  scoped to a user: `--user` only says whose sawa9ly session `sync` scrapes with.
  """

  @staticmethod
  def register(commands):
    shipping = commands.add_parser('shipping', help="delivery prices per wilaya")
    actions = shipping.add_subparsers(dest='action', required=True)

    sync = actions.add_parser('sync', help="scrape the price list and save it")
    sync.add_argument('--user', help="the account to scrape as; defaults to the super admin")

    listing = actions.add_parser('list', help="list saved prices")
    listing.add_argument('--available', choices=('yes', 'no'), default=None,
                         help="only the wilayas the site delivers to, or only those it does not")

    actions.add_parser('wilayas', help="list the 58 wilayas")

    communes = actions.add_parser('communes', help="list communes, or one wilaya's")
    communes.add_argument('--wilaya-id', type=int, default=None,
                          help="only this wilaya's communes")

    actions.add_parser('seed', help="load the wilaya and commune reference data")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.models import Commune, DeliveryPrice, Wilaya

    if args.action == 'sync':
      with Cli.db() as db:
        Cli.user(db, args.user)
        rows = Shipping(Cli.livewire(args.user)).get_prices()
        DeliveryPrice.sync(db, rows)
        return {'synced': len(rows),
                'prices': [p.as_dict() for p in DeliveryPrice.all(db)]}

    if args.action == 'list':
      available = {'yes': True, 'no': False}.get(args.available)

      with Cli.db() as db:
        return {'prices': [p.as_dict() for p in DeliveryPrice.all(db, available)]}

    if args.action == 'wilayas':
      with Cli.db() as db:
        return {'wilayas': [w.as_dict() for w in Wilaya.all(db)]}

    if args.action == 'communes':
      with Cli.db() as db:
        return {'communes': [c.as_dict() for c in Commune.all(db, args.wilaya_id)]}

    if args.action == 'seed':
      # Deliberately needs no client. The seed is plain SQL and can be handed to
      # sqlite3 or psql, but the application image carries neither, so on a VPS the
      # only thing available inside the container is the Python this command is
      # already running in. It uses the configured DATABASE_URL, so it is the same
      # database the application reads whichever engine that points at.
      with Cli.db() as db:
        return Seed.load(db)