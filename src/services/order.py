"""Order service: build a draft order locally, then post it to the site."""

from src.models import Client, Order, OrderLine, OrderState, Product
from src.services.cart import Cart
from src.services.product import Product as ProductPage
from src.utils.livewire import Livewire, LivewireError


class OrderError(Exception):
  """Raised when an order cannot be built or submitted."""


class OrderService:
  """Everything that happens to a stored order.

  A draft order is assembled in the database and edited freely. Submitting it
  (`checkout`) pushes the lines to the site's cart, fills the checkout form
  from the order's client, and posts it. After a successful submit the order
  becomes `confirmed` and is no longer editable.
  """

  # --- reading --------------------------------------------------------

  @staticmethod
  def get(db, order_id):
    order = Order.get(db, order_id)
    if order is None:
      raise OrderError(f"No order with id {order_id}")
    return order

  @staticmethod
  def list(db, user_id=None, state=None):
    return Order.all(db, user_id, state)

  # --- draft editing ---------------------------------------------------

  @staticmethod
  def _editable(order):
    if not order.is_editable():
      raise OrderError(
        f"Order {order.id} is {order.state!r} and can no longer be edited"
      )
    return order

  @staticmethod
  def _line(db, order, product_id):
    """Find an order line by the *sawa9ly* product id.

    Callers only ever know the site's product id, but a line is keyed by the
    internal products.id, so the two have to be translated.
    """
    product = Product.get(db, product_id)

    if product is None:
      return None

    return OrderLine.get(db, order.id, product.id)

  @staticmethod
  def create(db, username, client_id=None, note=None):
    """Start a draft order for a user."""
    from src.models import User

    user = User.get(db, username)
    if user is None:
      raise OrderError(f"No user named {username!r}")

    if client_id is not None and Client.get(db, client_id) is None:
      raise OrderError(f"No client with id {client_id}")

    return Order.create(db, user.id, client_id=client_id, note=note)

  @staticmethod
  def add_line(db, order_id, product_id, quantity=1, price=None):
    """Add a product to a draft order, or top up an existing line."""
    order = OrderService._editable(OrderService.get(db, order_id))
    product = Product.get_or_create(db, product_id)

    line = OrderLine.get(db, order.id, product.id)

    if line is None:
      line = OrderLine(order_id=order.id, product_id=product.id, quantity=quantity, price=price)
      db.add(line)
    else:
      line.quantity += quantity
      if price is not None:
        line.price = price

    db.commit()

    # The session keeps identity-mapped objects, so the order's already-loaded
    # `lines` collection would still be missing what was just inserted.
    db.expire(order, ["lines"])

    return order

  @staticmethod
  def remove_line(db, order_id, product_id):
    """Remove a product from a draft order."""
    order = OrderService._editable(OrderService.get(db, order_id))
    line = OrderService._line(db, order, product_id)

    if line is None:
      raise OrderError(f"Order {order.id} has no line for product {product_id}")

    db.delete(line)
    db.commit()
    db.expire(order, ["lines"])

    return order

  @staticmethod
  def set_quantity(db, order_id, product_id, quantity):
    """Set a line's quantity on a draft order."""
    order = OrderService._editable(OrderService.get(db, order_id))
    line = OrderService._line(db, order, product_id)

    if line is None:
      raise OrderError(f"Order {order.id} has no line for product {product_id}")

    if quantity < 1:
      raise OrderError("Quantity must be at least 1")

    line.quantity = quantity
    db.commit()
    db.expire(order, ["lines"])

    return order

  @staticmethod
  def set_price(db, order_id, product_id, price):
    """Set a line's unit price on a draft order."""
    order = OrderService._editable(OrderService.get(db, order_id))
    line = OrderService._line(db, order, product_id)

    if line is None:
      raise OrderError(f"Order {order.id} has no line for product {product_id}")

    if price < 1:
      raise OrderError("Price must be at least 1")

    line.price = price
    db.commit()
    db.expire(order, ["lines"])

    return order

  @staticmethod
  def set_state(db, order_id, state):
    """Move an order to another state, honouring the state machine."""
    return OrderService.get(db, order_id).transition(db, state)

  # --- submitting ------------------------------------------------------

  @staticmethod
  def _cart_for(username):
    """The site's cart for the user who owns this order."""
    return Cart(client=Livewire(username))

  @staticmethod
  def checkout(db, order_id, username, dry_run=False):
    """Post a draft order to the site.

    Mirrors the site's own flow: the lines are pushed into the cart with their
    quantities, the client fills the checkout form, and the order is
    submitted. A successful submit moves the order to `confirmed`; prices live
    only in the Livewire snapshot, so this is the step that commits them.

    Args:
        db: An open database session.
        order_id: The draft to submit.
        username: Whose sawa9ly session to drive. Defaults to the order's owner.
        dry_run: Stop after the cart is staged, before submitting.

    Returns:
        The site checkout result, plus the order's new state.
    """
    order = OrderService.get(db, order_id)

    if not order.is_editable():
      raise OrderError(f"Order {order.id} is {order.state!r}; only a draft can be submitted")

    if not order.lines:
      raise OrderError(f"Order {order.id} has no lines to submit")

    client_row = order.client
    if client_row is None:
      raise OrderError(f"Order {order.id} has no client to deliver to")

    owner = order.user.username if username is None else username
    cart = OrderService._cart_for(owner)

    # Pushing the lines: the site's cart is per session, so clear whatever is
    # there and rebuild it from this order before submitting.
    OrderService._sync_cart(cart, order)

    # The site addresses products by their sawa9ly id, but a line is keyed by
    # the internal products.id, so translate before talking to it.
    quantities = {
      line.product.product_id: line.quantity for line in order.lines
    }
    prices = {
      line.product.product_id: line.price
      for line in order.lines if line.price is not None
    }

    result = cart.checkout(
      quantities=quantities,
      prices=prices,
      client=client_row.checkout_fields(),
      dry_run=dry_run,
    )

    if dry_run:
      return {'order': order.as_dict(), 'checkout': result, 'state': order.state}

    if result.get('success'):
      order.reference = str(result.get('order') or '') or None
      order.transition(db, OrderState.CONFIRMED)

    return {'order': order.as_dict(), 'checkout': result, 'state': order.state}

  @staticmethod
  def _sync_cart(cart, order):
    """Make the site's cart match a draft order exactly.

    Products are added and sized in one pass, and any line the order no longer
    contains is removed, so what gets submitted is exactly this draft.
    """
    try:
      current = cart.get_info()['quantities']
    except LivewireError:
      current = {}

    # A line's product_id is the internal products.id; the site wants the
    # sawa9ly one.
    wanted = {line.product.product_id: line.quantity for line in order.lines}

    # Drop anything the order does not want.
    for product_id in set(current) - set(wanted):
      cart.remove_item(product_id)

    # Add and size the lines the order wants.
    for product_id, quantity in wanted.items():
      if product_id in current:
        cart.update_item_quantity(product_id, quantity)
      else:
        ProductPage(product_id, client=cart.client).add_to_cart()
        if quantity != 1:
          cart.update_item_quantity(product_id, quantity)
