"""Cart page model."""

import json
import logging

from src.utils import BASE_URL, Selector
from src.utils.livewire import LivewireError

logger = logging.getLogger(__name__)

PANIER_COMPONENT = "panier"

# Cart selectors depend on the item id, so they live here as templates rather
# than in the static `guide`. The quantity and price inputs bind through
# wire:model.live, so those attribute names contain dots that cssselect needs
# escaped.
QUANTITY_INPUT = 'input[wire\\:model\\.live="products_quantity.{item_id}"]'
PRICE_INPUT = 'input[wire\\:model\\.live\\.debounce\\.500ms="free_commission_prices.{item_id}"]'
REMOVE_BUTTON = '[wire\\:click="removeFromCart({item_id})"]'

CHECKOUT_FIELDS = ('full_name', 'phone', 'adresse', 'wilaya_id', 'commune_id', 'note')

MAX_STEPS = 50

INVALID_PRICE = "Price must be an integer of at least 1"
INVALID_QUANTITY = "Quantity must be an integer of at least 1"
NOT_IN_CART = "Item is not in the cart"


class Cart(Selector):

  guide = {}
  url = f"{BASE_URL}/panier"

  def __init__(self, client):
    super().__init__(client)

  def get_info(self):
    """Read the cart's lines, unit prices and total."""
    data = self._snapshot()
    item_ids = _item_ids(data)
    prices = _as_int_map(data.get('free_commission_prices'))

    return {
      'quantities': _present_quantities(data),
      'prices': {item_id: prices[item_id] for item_id in item_ids if item_id in prices},
      'count': len(item_ids),
      'total': data.get('total'),
    }

  def update_item_quantity(self, item_id, quantity):
    """Set a line's quantity, persistently.

    The quantity input is bound with wire:model.live, but that only mutates
    the client-held snapshot: it neither recomputes the total nor survives a
    reload. The server-side cart is only changed by the incrementQuantity /
    decrementQuantity actions the +/- buttons call, one unit per request, so
    this steps to the target one unit at a time.

    Args:
        item_id (str | int): The product id of the cart line.
        quantity (int | str): The new quantity, at least 1.

    Returns:
        dict: {'item_id', 'quantity', 'total'} with the server's values.

    Raises:
        LivewireError: If the quantity is invalid, the item is not in the
            cart, the delta is too large, or a call fails.
    """
    item_id = int(item_id)
    quantity = _validate(quantity, INVALID_QUANTITY)

    self.refresh()
    component = self._component()

    if not len(self.doc(QUANTITY_INPUT.format(item_id=item_id))):
      raise LivewireError(NOT_IN_CART)

    current = _present_quantities(self._snapshot()).get(item_id, 0)
    delta = quantity - current

    if abs(delta) > MAX_STEPS:
      raise LivewireError(
        f"Refusing to move quantity by {delta}: each unit is a request "
        f"and the limit is {MAX_STEPS}"
      )

    method = "incrementQuantity" if delta > 0 else "decrementQuantity"
    snapshot = self.client.snapshot_of(component)
    data = self._snapshot()

    for _ in range(abs(delta)):
      result = self.client.call(self.html, snapshot, method, [item_id], referer=self.url)
      snapshot = result["components"][0]["snapshot"]
      data = self.client.component_data(result)

      stepped = _present_quantities(data).get(item_id, 0)
      if stepped == current:
        logger.warning(
          "cart for %s: the server stopped moving item %s at quantity %s",
          self.client.username, item_id, current,
        )
        break  # server refused to move further, e.g. a stock ceiling

      current = stepped

    return {
      'item_id': item_id,
      'quantity': _present_quantities(data).get(item_id, 0),
      'total': data.get('total'),
    }

  def update_item_price(self, item_id, price):
    """Set a line's unit price.

    The cart exposes no server-side action for the price: the
    free_commission_prices input is bound with wire:model.live, so the new
    value lives in the client-held snapshot, is reflected in the total the
    server returns for that request, and is carried into checkout from there.
    It does not survive a page reload.

    Args:
        item_id (str | int): The product id of the cart line.
        price (int | str): The new unit price, at least 1.

    Returns:
        dict: {'item_id', 'price', 'total'} as returned for that request.

    Raises:
        LivewireError: If the price is invalid, the item is not in the cart,
            or the call fails.
    """
    item_id = int(item_id)
    price = _validate(price, INVALID_PRICE)

    self.refresh()
    component = self._component()

    if not len(self.doc(PRICE_INPUT.format(item_id=item_id))):
      raise LivewireError(NOT_IN_CART)

    result = self.client.update(
      self.html, component,
      {f"free_commission_prices.{item_id}": str(price)},
      referer=self.url,
    )
    data = self.client.component_data(result)

    return {
      'item_id': item_id,
      'price': _as_int_map(data.get('free_commission_prices')).get(item_id),
      'total': data.get('total'),
    }

  def remove_item(self, item_id):
    """Remove a line from the cart.

    Raises:
        LivewireError: If the item is not in the cart or the call fails.
    """
    item_id = int(item_id)

    self.refresh()
    component = self._component()

    if not len(self.doc(REMOVE_BUTTON.format(item_id=item_id))):
      raise LivewireError(NOT_IN_CART)

    result = self.client.call(self.html, component, "removeFromCart", [item_id], referer=self.url)
    data = self.client.component_data(result)

    return {
      'item_id': item_id,
      'quantities': _present_quantities(data),
      'total': data.get('total'),
    }

  def checkout(self, quantities=None, prices=None, client=None, dry_run=False):
    """Set the line quantities and prices, fill the order form and submit it.

    Neither value survives on the cart page itself, so both are applied here
    just before submitting, each by the route the server actually reads:
    quantities through the +/- actions (the server reads them from the cart)
    and prices through an updates push (the server reads them from the
    component state). Prices must also leave the order commission at or
    above the site's 5% minimum or next_step refuses to advance.

    Args:
        quantities (dict): {product_id: quantity} to set before submitting.
        prices (dict): {product_id: unit price} to set before submitting.
        client (dict): any of full_name, phone, adresse, wilaya_id,
            commune_id, note. Everything the order requires must be present
            or the server rejects the submit with validation errors.
        dry_run (bool): stage the lines and stop before the form, leaving no
            chance of placing an order.

    Returns:
        dict: {'success', 'order', 'step', 'total', 'errors'}.

    Raises:
        LivewireError: If an item is not in the cart, a quantity or price is
            invalid, the form step cannot be reached, or a call fails.
    """
    quantities = quantities or {}
    prices = prices or {}
    client = client or {}

    logger.info(
      "checkout for %s: staging %d line(s) and %d price(s)%s",
      self.client.username, len(quantities), len(prices),
      " (dry run)" if dry_run else "",
    )

    self.refresh()
    item_ids = set(_item_ids(self._snapshot()))

    unknown = (set(int(item_id) for item_id in quantities)
               | set(int(item_id) for item_id in prices)) - item_ids

    if unknown:
      raise LivewireError(f"Items not in the cart: {sorted(unknown)}")

    # Quantities are read by the server from the cart itself, so an updates
    # push only moves the on-screen mirror and never the total. They have to
    # go through the +/- actions to reach the order.
    for item_id, quantity in quantities.items():
      self.update_item_quantity(item_id, quantity)

    self.refresh()
    component = self._component()

    # Prices, unlike quantities, are read from the component state, so an
    # updates push is what puts them on the order.
    staged = {
      f"free_commission_prices.{int(item_id)}": str(_validate(price, INVALID_PRICE))
      for item_id, price in prices.items()
    }

    result = self.client._dispatch(
      self.html, self.client.snapshot_of(component),
      updates=staged,
      calls=[{"path": "", "method": "next_step", "params": []}],
      referer=self.url, label="checkout (items)",
    )
    data = self.client.component_data(result)

    if dry_run or data.get('step') != 2:
      # next_step refused to advance, e.g. the prices leave the commission
      # under the site's 5% minimum. The response carries the reason.
      result = _checkout_result(data, result)

      logger.info(
        "checkout for %s: stopped at step %s before the form (%s), "
        "%d field error(s)",
        self.client.username, result['step'],
        "dry run" if dry_run else "next_step refused to advance",
        len(result['errors']),
      )

      return result

    # wilaya_id drives the commune options, so it goes on its own before
    # commune_id, mirroring the order the browser builds the form in.
    snapshot = result["components"][0]["snapshot"]
    fields = {name: client[name] for name in CHECKOUT_FIELDS
              if name in client and name != 'commune_id'}

    result = self.client._dispatch(
      self.html, snapshot, updates=fields,
      referer=self.url, label="checkout (client)",
    )
    snapshot = result["components"][0]["snapshot"]

    submitted = {'commune_id': client['commune_id']} if 'commune_id' in client else {}

    result = self.client._dispatch(
      self.html, snapshot,
      updates=submitted,
      calls=[{"path": "", "method": "submit", "params": []}],
      referer=self.url, label="checkout (submit)",
    )

    result = _checkout_result(self.client.component_data(result), result)

    logger.info(
      "checkout for %s: submitted, success=%s, order=%s, %d field error(s)",
      self.client.username, result['success'], result['order'],
      len(result['errors']),
    )

    return result

  def _component(self):
    component = self.client.find_component(self.doc, PANIER_COMPONENT)
    if component is None:
      raise LivewireError("Cart component not found")

    return component

  def _snapshot(self):
    return json.loads(self.client.snapshot_of(self._component()))["data"]


def _checkout_result(data, response):
  """Read the outcome of a checkout step out of a Livewire response.

  Livewire reports validation failures in the snapshot's memo rather than as
  an HTTP error, so the caller has to look there for them.
  """
  snapshot = json.loads(response["components"][0]["snapshot"])

  return {
    'success': bool(data.get('success')),
    'order': data.get('order'),
    'step': data.get('step'),
    'total': data.get('total'),
    'errors': snapshot['memo'].get('errors') or {},
  }


def _item_ids(data):
  """The product ids currently in the cart.

  `cart_items` is an Eloquent collection serialised down to its keys. It is
  the only reliable membership source: `products_quantity` keeps a stale
  entry for removed items, while `free_commission_prices` is filtered.
  """
  cart_items = data.get('cart_items') or []
  if not isinstance(cart_items, list) or len(cart_items) < 2:
    return []

  meta = cart_items[1]
  if not isinstance(meta, dict):
    return []

  return [int(item_id) for item_id in meta.get('keys', [])]


def _present_quantities(data):
  """The quantity map narrowed to the products actually in the cart."""
  quantities = _as_int_map(data.get('products_quantity'))

  return {item_id: quantities.get(item_id, 0) for item_id in _item_ids(data)}


def _as_int_map(value):
  """Read a Livewire array payload, which is wrapped as [data, {"s": …}]."""
  if not isinstance(value, list) or not value:
    return {}

  payload = value[0]
  if not isinstance(payload, dict):
    return {}

  return {int(key): int(quantity) for key, quantity in payload.items()}


def _validate(value, message):
  try:
    number = int(str(value).strip())
  except (TypeError, ValueError):
    raise LivewireError(f"{message}, got {value!r}")

  if number < 1:
    raise LivewireError(f"{message}, got {value!r}")

  return number
