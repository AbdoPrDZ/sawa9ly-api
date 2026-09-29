"""CLI: product scraping and cart operations."""

from src.services import Cart
from src.services import Product as ProductPage


class ProductCli:
  """`product`, `cart` and `checkout`.

  Every command here acts on a user's site session, so every command requires
  `--user`. There is no default account.

  The cart's operations are nested under `cart` rather than spelled out as
  `cart-add`, `cart-remove` and so on. Flat names that all start with the same
  word are one namespace pretending to be six, and they sort together in
  `--help` instead of grouping under the thing they act on — the same shape every
  other resource in this CLI already uses (`order`, `client`, `page`).
  """

  @staticmethod
  def register(commands):
    commands.add_parser('login', help="log in, refresh the stored session and print the cookie").add_argument(
      '--user', help="the account to act as; defaults to the super admin"
    )

    product = commands.add_parser('product', help="scrape a product page")
    product.add_argument('product_id', nargs='?')
    product.add_argument('--user', help="the account to act as; defaults to the super admin")

    cart = commands.add_parser('cart', help="the site's cart")
    actions = cart.add_subparsers(dest='action', required=True)

    # `add` and `remove` go through the product page, so their product id is
    # optional and falls back to the error that names it — same as
    # `python main.py product`.
    add = actions.add_parser('add', help="add a product to the cart")
    add.add_argument('product_id', nargs='?')
    add.add_argument('--user', help="the account to act as; defaults to the super admin")

    remove = actions.add_parser('remove', help="remove a product from the cart (product page)")
    remove.add_argument('product_id', nargs='?')
    remove.add_argument('--user', help="the account to act as; defaults to the super admin")

    set_quantity = actions.add_parser('set-quantity', help="update a cart line quantity")
    set_quantity.add_argument('product_id')
    set_quantity.add_argument('quantity')
    set_quantity.add_argument('--user', help="the account to act as; defaults to the super admin")

    set_price = actions.add_parser('set-price', help="update a cart line unit price")
    set_price.add_argument('product_id')
    set_price.add_argument('price')
    set_price.add_argument('--user', help="the account to act as; defaults to the super admin")

    remove_item = actions.add_parser('remove-item', help="remove a cart line (cart page)")
    remove_item.add_argument('product_id')
    remove_item.add_argument('--user', help="the account to act as; defaults to the super admin")

    show = actions.add_parser('show', help="show the cart")
    show.add_argument('--user', help="the account to act as; defaults to the super admin")

    checkout = commands.add_parser('checkout', help="set quantities/prices, fill the form and submit")
    checkout.add_argument('--quantities', default='{}', help='JSON map of product id to quantity')
    checkout.add_argument('--prices', default='{}', help='JSON map of product id to unit price')
    checkout.add_argument('--client', default='{}', help='JSON map of the order form fields')
    checkout.add_argument('--dry-run', action='store_true',
                          help="stage the lines and stop before the form")
    checkout.add_argument('--user', help="the account to act as; defaults to the super admin")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli

    cart = Cart(client=Cli.livewire(args.user))

    if args.command == 'login':
      return {'cookies': cart.client.login()}

    if args.command == 'product':
      return ProductPage(Cli.product_id_of(args), cart.client).get_info()

    if args.command == 'cart':
      if args.action == 'show':
        return cart.get_info()

      if args.action == 'add':
        return ProductPage(Cli.product_id_of(args), cart.client).add_to_cart()

      if args.action == 'remove':
        return ProductPage(Cli.product_id_of(args), cart.client).remove_from_cart()

      if args.action == 'set-quantity':
        return cart.update_item_quantity(args.product_id, args.quantity)

      if args.action == 'set-price':
        return cart.update_item_price(args.product_id, args.price)

      if args.action == 'remove-item':
        return cart.remove_item(args.product_id)

      raise SystemExit(f"error: unknown cart action: {args.action}")

    if args.command == 'checkout':
      return cart.checkout(
        quantities=Cli.json_map(args.quantities, '--quantities'),
        prices=Cli.json_map(args.prices, '--prices'),
        client=Cli.json_map(args.client, '--client'),
        dry_run=args.dry_run,
      )
