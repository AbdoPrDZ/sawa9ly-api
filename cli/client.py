"""CLI: delivery recipients."""

class ClientCli:
  """`client` — the people orders are shipped to."""

  @staticmethod
  def register(commands):
    client = commands.add_parser('client', help="delivery recipients")
    actions = client.add_subparsers(dest='action', required=True)

    add = actions.add_parser('add', help="add or update a client")
    add.add_argument('full_name')
    add.add_argument('--phone', default=None)
    add.add_argument('--adresse', default=None)
    add.add_argument('--wilaya-id', type=int, default=None)
    add.add_argument('--commune-id', type=int, default=None)
    add.add_argument('--note', default=None)
    add.add_argument('--user', help="the account to act as; defaults to the super admin")

    listing = actions.add_parser('list', help="list a user's clients")
    listing.add_argument('--user', help="the account to act as; defaults to the super admin")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.models import Client

    with Cli.db() as db:
      user = Cli.user(db, args.user)

      if args.action == 'add':
        client = Client.get_or_create(
          db, user.id, args.full_name,
          phone=args.phone, adresse=args.adresse,
          wilaya_id=args.wilaya_id, commune_id=args.commune_id, note=args.note,
        )
        return client.as_dict()

      if args.action == 'list':
        return {'clients': [c.as_dict() for c in Client.all(db, user.id)]}
