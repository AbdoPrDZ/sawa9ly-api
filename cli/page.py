"""CLI: landing pages."""

from src.services import LandingPageService


class PageCli:
  """`page` — a user's own landing pages for the catalogue's products."""

  @staticmethod
  def register(commands):
    page = commands.add_parser('page', help="landing pages")
    actions = page.add_subparsers(dest='action', required=True)

    create = actions.add_parser('create', help="start a draft page")
    create.add_argument('product_id', help="the sawa9ly product id")
    create.add_argument('title')
    create.add_argument('--html', default='', help="the page markup; omit for an empty page")
    create.add_argument('--user', help="whose page it is; defaults to the super admin")

    show = actions.add_parser('show', help="show a page")
    show.add_argument('page_id', type=int)

    edit = actions.add_parser('edit', help="change a page's title or markup")
    edit.add_argument('page_id', type=int)
    edit.add_argument('--title', default=None)
    edit.add_argument('--html', default=None)

    state = actions.add_parser('state', help="move a page to another state")
    state.add_argument('page_id', type=int)
    state.add_argument('state', choices=['draft', 'publish', 'archive'])

    listing = actions.add_parser('list', help="list a user's pages")
    listing.add_argument('--user', help="whose pages to list; defaults to the super admin")
    listing.add_argument('--product', type=int, default=None,
                         help="only pages for this sawa9ly product id")
    listing.add_argument('--state', default=None)

  @staticmethod
  def dispatch(args):
    from cli.base import Cli

    with Cli.db() as db:
      if args.action == 'create':
        return LandingPageService.create(
          db, args.user, args.product_id, args.title, args.html
        ).as_dict()

      if args.action == 'show':
        return LandingPageService.get(db, args.page_id).as_dict()

      if args.action == 'edit':
        return LandingPageService.update(
          db, args.page_id, title=args.title, html=args.html
        ).as_dict()

      if args.action == 'state':
        return LandingPageService.set_state(db, args.page_id, args.state).as_dict()

      if args.action == 'list':
        user = Cli.user(db, args.user)

        # The filters are the sawa9ly product id and a state name, so the
        # sawa9ly id is translated to our own key before the query runs.
        product_pk = None
        if args.product is not None:
          from src.models import Product

          product = Product.get(db, args.product)
          product_pk = product.id if product else -1

        return {
          'pages': [
            p.as_dict()
            for p in LandingPageService.list(db, user.id, product_pk, args.state)
          ]
        }
