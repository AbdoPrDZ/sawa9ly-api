"""CLI: orders."""

from src.services import OrderService


class OrderCli:
  """`order` — build a draft, edit it, then submit it to the site."""

  @staticmethod
  def register(commands):
    order = commands.add_parser('order', help="orders")
    actions = order.add_subparsers(dest='action', required=True)

    create = actions.add_parser('create', help="start a draft order")
    create.add_argument('--client', type=int, default=None)
    create.add_argument('--user', required=True, help="whose order it is")

    add = actions.add_parser('add', help="add a product to a draft order")
    add.add_argument('order_id', type=int)
    add.add_argument('product_id')
    add.add_argument('--quantity', type=int, default=1)
    add.add_argument('--price', type=int, default=None)

    remove = actions.add_parser('remove', help="remove a product from a draft order")
    remove.add_argument('order_id', type=int)
    remove.add_argument('product_id')

    set_quantity = actions.add_parser('set-quantity', help="set a draft order line's quantity")
    set_quantity.add_argument('order_id', type=int)
    set_quantity.add_argument('product_id')
    set_quantity.add_argument('quantity', type=int)

    set_price = actions.add_parser('set-price', help="set a draft order line's price")
    set_price.add_argument('order_id', type=int)
    set_price.add_argument('product_id')
    set_price.add_argument('price', type=int)

    checkout = actions.add_parser('checkout', help="submit a draft order to the site")
    checkout.add_argument('order_id', type=int)
    checkout.add_argument('--dry-run', action='store_true')
    checkout.add_argument('--user', required=True, help="whose sawa9ly session to use")

    state = actions.add_parser('state', help="move an order to another state")
    state.add_argument('order_id', type=int)
    state.add_argument('state', choices=['draft', 'confirmed', 'done'])

    listing = actions.add_parser('list', help="list orders")
    listing.add_argument('--user', required=True, help="whose orders to list")
    listing.add_argument('--state', default=None)

    show = actions.add_parser('show', help="show an order")
    show.add_argument('order_id', type=int)

  @staticmethod
  def dispatch(args):
    from cli.base import Cli

    with Cli.db() as db:
      if args.action == 'create':
        return OrderService.create(db, args.user, client_id=args.client).as_dict()

      if args.action == 'add':
        return OrderService.add_line(db, args.order_id, args.product_id,
                                     args.quantity, args.price).as_dict()

      if args.action == 'remove':
        return OrderService.remove_line(db, args.order_id, args.product_id).as_dict()

      if args.action == 'set-quantity':
        return OrderService.set_quantity(db, args.order_id, args.product_id,
                                         args.quantity).as_dict()

      if args.action == 'set-price':
        return OrderService.set_price(db, args.order_id, args.product_id,
                                      args.price).as_dict()

      if args.action == 'checkout':
        return OrderService.checkout(db, args.order_id, username=args.user,
                                     dry_run=args.dry_run)

      if args.action == 'state':
        return OrderService.set_state(db, args.order_id, args.state).as_dict()

      if args.action == 'list':
        user = Cli.user(db, args.user)
        orders = OrderService.list(db, user.id, args.state)
        return {'orders': [o.as_dict() for o in orders]}

      if args.action == 'show':
        return OrderService.get(db, args.order_id).as_dict()
