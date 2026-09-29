"""Order service: build a draft order locally, then post it to the site."""

import logging

from src.models import Client, Order, OrderLine, OrderState, Product
from src.services.cart import Cart
from src.services.product import Product as ProductPage
from src.utils.livewire import Livewire, LivewireError

#: The site's own order page, keyed by the id the site generated. Kept here so
#: the one place that knows the shape of the site's URLs is the one place that
#: has to know it.
logger = logging.getLogger(__name__)


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
  def add_line(db, order_id, product_id, quantity=1, price=None, note=None):
    """Add a product to a draft order, or top up an existing line.

    `note` follows the same rule as `price` on a line that already exists: it is
    only written when given, so topping up a quantity cannot silently wipe the
    reason it was there.

    `origin_price` is snapshotted **only when the line is created**, from the
    catalogue's price for that product at this moment. A top-up deliberately
    leaves it alone: the line already records what the site charged the first
    time, and a later price is a different fact. A product that is not in the
    catalogue yet has no price to snapshot and gets a null, which is also what a
    product showing "sur demande" gets — unknown, not zero.
    """
    order = OrderService._editable(OrderService.get(db, order_id))
    product = Product.get_or_create(db, product_id)

    line = OrderLine.get(db, order.id, product.id)

    if line is None:
      line = OrderLine(
        order_id=order.id, product_id=product.id,
        quantity=quantity, price=price, note=note,
        origin_price=product.numeric_price(),
      )
      db.add(line)
    else:
      line.quantity += quantity
      if price is not None:
        line.price = price
      if note is not None:
        line.note = note

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
      order.origin_id = OrderService._origin_id(result)
      order.reference = OrderService._reference(result, order.origin_id)
      order.transition(db, OrderState.CONFIRMED)

      if order.origin_id is None:
        # Not a failure — the order really was placed, we just could not read
        # its number. Say so, because an order with no id is one the site cannot
        # be asked about later.
        logger.warning(
          "checkout for %s: placed, but no order id in the response (order=%r)",
          username, result.get('order'),
        )
      else:
        logger.info(
          "checkout for %s: placed as order %s (reference %r)",
          username, order.origin_id, order.reference,
        )

    return {'order': order.as_dict(), 'checkout': result, 'state': order.state}

  @staticmethod
  def _origin_id(result):
    """The order number the website generated, or None.

    The site does not return a bare number. Its `order` value is a PHP array
    carrying a serialised Eloquent model, which arrives as
    `[None, {'class': 'App\\\\Models\\\\Order', 'key': 879988, 's': 'mdl'}]` — the
    id is the `key` of the model in it.

    So the shape is searched rather than assumed: a number, a string of digits,
    a mapping, or a sequence holding one. Every plausible arrangement is handled
    and anything else is None.

    None is always better than a wrong id. A wrong one would be believed, stored,
    and used to ask the site about an order that is not this one.
    """
    value = result.get('order')

    if value is None or isinstance(value, bool):
      return None

    if isinstance(value, int):
      return value

    if isinstance(value, str):
      text = value.strip()
      return int(text) if text.isdigit() else None

    if isinstance(value, dict):
      return OrderService._id_in(value)

    if isinstance(value, (list, tuple)):
      for element in value:
        found = OrderService._id_in(element) if isinstance(element, dict) else (
          element if isinstance(element, int) and not isinstance(element, bool) else None
        )
        if found is not None:
          return found

    return None

  @staticmethod
  def _id_in(model):
    """The id inside a serialised Eloquent model, or None.

    `key` is what the site puts the primary key in. `id` and `order_id` are here
    for a site that sends something plainer, and cost nothing to try.
    """
    for key in ("key", "id", "order_id"):
      candidate = model.get(key)

      if isinstance(candidate, bool):
        continue

      if isinstance(candidate, int):
        return candidate

      if isinstance(candidate, str) and candidate.strip().isdigit():
        return int(candidate.strip())

    return None

  @staticmethod
  def _reference(result, origin_id):
    """The human-readable reference, when the site gave one worth keeping.

    Only a plain scalar is stored. The site normally returns the serialised model
    described above, and stringifying that produced a Python repr of a PHP array
    in a field meant to hold a reference — noise that read like a bug. When there
    is no clean scalar the id lives in `origin_id` and this stays null, which is
    the honest answer rather than a blob.
    """
    value = result.get('order')

    if isinstance(value, str) and value.strip():
      return value.strip()[:128]

    if isinstance(value, int) and not isinstance(value, bool):
      return str(value)

    return str(origin_id) if origin_id is not None else None

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
