"""CLI: the saved product catalogue."""

from src.services import Product as ProductPage


class CatalogueCli:
  """`catalogue` — scrape a product once, then read it back from the database."""

  @staticmethod
  def register(commands):
    catalogue = commands.add_parser('catalogue', help="saved product info")
    actions = catalogue.add_subparsers(dest='action', required=True)

    save = actions.add_parser('save', help="scrape a product and save it")
    save.add_argument('product_id', nargs='?')
    save.add_argument('--user', help="the account to scrape as; defaults to the super admin")

    show = actions.add_parser('show', help="show a saved product")
    show.add_argument('product_id')

    price = actions.add_parser('set-price', help="set a product's sell price")
    price.add_argument('product_id')
    price.add_argument('price', type=int)

    actions.add_parser('list', help="list saved products")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.models import Product

    if args.action == 'save':
      with Cli.db() as db:
        Cli.user(db, args.user)
        product_id = Cli.product_id_of(args)
        info = ProductPage(product_id, Cli.livewire(args.user)).get_info()
        return Product.save(db, product_id, info).as_dict()

    if args.action == 'show':
      with Cli.db() as db:
        product = Product.get(db, args.product_id)

        if product is None:
          raise SystemExit(f"error: product {args.product_id} is not saved")

        return product.as_dict()

    if args.action == 'set-price':
      with Cli.db() as db:
        product = Product.get(db, args.product_id)

        if product is None:
          raise SystemExit(f"error: product {args.product_id} is not saved")

        return product.set_price(db, args.price).as_dict()

    if args.action == 'list':
      with Cli.db() as db:
        return {'products': [p.as_dict() for p in Product.all(db)]}
