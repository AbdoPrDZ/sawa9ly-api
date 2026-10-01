"""Orders, as MCP tools.

The eight operations the HTTP API exposes under `/api/v1/orders`. A draft is
assembled and edited here in the database; `checkout_order` is what sends it to
the site, and it is the only tool here that can place a real order.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.models import Order as OrderRow
from src.services import OrderService


class OrdersTools:
  """Building a draft order and submitting it to the site."""

  @staticmethod
  def list_orders(q: str = None, limit: int = None, offset: int = None):
    """The caller's own orders, newest first.

    `q` searches the order id and the site reference; `limit` and `offset` page
    the result. Passing none of them returns every row.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return OrderRow.page(db, user_id=user.id, limit=limit, offset=offset,
                           search=q).as_dict(lambda order: order.as_dict())

  @staticmethod
  def create_order(client_id: int = None, note: str = None):
    """Start a draft order, optionally addressed to a saved client.

    Nothing reaches sawa9ly.app until checkout. `client_id` is the caller's own
    `get_client` result; the order form is filled from that row at checkout.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return OrderService.create(db, user.username, client_id=client_id,
                                 note=note).as_dict()

  @staticmethod
  def get_order(order_id: int):
    """One order, with its lines in full."""
    user = McpAuth.user()

    with session_scope() as db:
      return OrdersTools._owned(db, order_id, user.id).as_dict()

  @staticmethod
  def add_order_line(order_id: int, product_id: int, quantity: int = 1,
                     price: int = None, note: str = None):
    """Add a product to a draft order.

    `product_id` is the sawa9ly id, as everywhere else. A product that has never
    been scraped gets a catalogue stub row rather than being refused, so an order
    can be written before anyone looks at the page.
    """
    user = McpAuth.user()

    with session_scope() as db:
      OrdersTools._owned(db, order_id, user.id)

      return OrderService.add_line(db, order_id, product_id, quantity=quantity,
                                   price=price, note=note).as_dict()

  @staticmethod
  def remove_order_line(order_id: int, product_id: int):
    """Remove a product from a draft order, addressed by product id."""
    user = McpAuth.user()

    with session_scope() as db:
      OrdersTools._owned(db, order_id, user.id)

      return OrderService.remove_line(db, order_id, product_id).as_dict()

  @staticmethod
  def set_order_line_quantity(order_id: int, product_id: int, quantity: int):
    """Set a draft order line's quantity. At least 1."""
    user = McpAuth.user()

    with session_scope() as db:
      OrdersTools._owned(db, order_id, user.id)

      return OrderService.set_quantity(db, order_id, product_id, quantity).as_dict()

  @staticmethod
  def set_order_line_price(order_id: int, product_id: int, price: int):
    """Set a draft order line's unit price, in whole dinars. At least 1.

    Left unset, the site decides the price, which is rarely what an order built
    by hand intends.
    """
    user = McpAuth.user()

    with session_scope() as db:
      OrdersTools._owned(db, order_id, user.id)

      return OrderService.set_price(db, order_id, product_id, price).as_dict()

  @staticmethod
  def checkout_order(order_id: int, dry_run: bool = False):
    """Submit a draft order to the site: fill the cart from its lines, fill the
    form from its client, and place it.

    A successful submit confirms the order, which is then no longer editable.

    **A call with dry_run false places a real order that cannot be cancelled from
    here.** Pass dry_run true first: it stages the cart and stops before the form,
    which is the only way to see what the site thinks the order costs before
    committing to it.
    """
    user = McpAuth.user()

    with session_scope() as db:
      OrdersTools._owned(db, order_id, user.id)

      return OrderService.checkout(db, order_id, username=user.username,
                                   dry_run=dry_run)

  @staticmethod
  def _owned(db, order_id, user_id):
    """The order, if the caller owns it. Otherwise absent, not forbidden."""
    order = OrderRow.get(db, order_id)

    if order is None or order.user_id != user_id:
      raise McpError(f"No such order: {order_id}")

    return order

  @staticmethod
  def tools():
    return (
      OrdersTools.list_orders,
      OrdersTools.create_order,
      OrdersTools.get_order,
      OrdersTools.add_order_line,
      OrdersTools.remove_order_line,
      OrdersTools.set_order_line_quantity,
      OrdersTools.set_order_line_price,
      OrdersTools.checkout_order,
    )
