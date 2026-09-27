"""CLI: product scraping and cart operations."""

from src.services import Cart
from src.services import Product as ProductPage


class ProductCli:
  """`product`, `cart` and the cart-line commands.

  Every command here acts on a user's site session, so every command requires
  `--user`. There is no default account.
  """

  @staticmethod
  def register(commands):
    for name, help_text in [
      ('cart', "show the cart"),
      ('login', "log in, refresh the stored session and print the cookie"),
    ]:
      commands.add_parser(name, help=help_text).add_argument(
        '--user', required=True, help="the account to act as"
      )

    for name, help_text in [
      ('product', "scrape a product page"),
      ('cart-add', "add a product to the cart"),
      ('cart-remove', "remove a product from the cart"),
    ]:
      command = commands.add_parser(name, help=help_text)
      command.add_argument('product_id', nargs='?')
      command.add_argument('--user', required=True, help="the account to act as")

    set_quantity = commands.add_parser('cart-set-quantity', help="update a cart line quantity")
    set_quantity.add_argument('product_id')
    set_quantity.add_argument('quantity')
    set_quantity.add_argument('--user', required=True, help="the account to act as")

    set_price = commands.add_parser('cart-set-price', help="update a cart line price")
    set_price.add_argument('product_id')
    set_price.add_argument('price')
    set_price.add_argument('--user', required=True, help="the account to act as")

    remove_item = commands.add_parser('cart-remove-item', help="remove a cart line")
    remove_item.add_argument('product_id')
    remove_item.add_argument('--user', required=True, help="the account to act as")

    checkout = commands.add_parser('checkout', help="set quantities/prices, fill the form and submit")
    checkout.add_argument('--quantities', default='{}', help='JSON map of product id to quantity')
    checkout.add_argument('--prices', default='{}', help='JSON map of product id to unit price')
    checkout.add_argument('--client', default='{}', help='JSON map of the order form fields')
    checkout.add_argument('--dry-run', action='store_true',
                          help="stage the lines and stop before the form")
    checkout.add_argument('--user', required=True, help="the account to act as")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli

    cart = Cart(client=Cli.livewire(args.user))

    if args.command == 'login':
      return {'cookies': cart.client.login()}

    if args.command == 'cart':
      return cart.get_info()

    if args.command == 'product':
      return ProductPage(Cli.product_id_of(args), cart.client).get_info()

    if args.command == 'cart-add':
      return ProductPage(Cli.product_id_of(args), cart.client).add_to_cart()

    if args.command == 'cart-remove':
      return ProductPage(Cli.product_id_of(args), cart.client).remove_from_cart()

    if args.command == 'cart-set-quantity':
      return cart.update_item_quantity(args.product_id, args.quantity)

    if args.command == 'cart-set-price':
      return cart.update_item_price(args.product_id, args.price)

    if args.command == 'cart-remove-item':
      return cart.remove_item(args.product_id)

    if args.command == 'checkout':
      return cart.checkout(
        quantities=Cli.json_map(args.quantities, '--quantities'),
        prices=Cli.json_map(args.prices, '--prices'),
        client=Cli.json_map(args.client, '--client'),
        dry_run=args.dry_run,
      )
