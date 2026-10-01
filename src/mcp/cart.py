"""The site's cart, as MCP tools.

The four operations the HTTP API exposes under `/api/v1/cart`. They read and
edit the cart that lives inside the caller's own sawa9ly session, so there is
nothing to store and nothing to refresh: every call is a round trip to the site.
"""

from src.mcp.auth import McpAuth


class CartTools:
  """Reading the caller's cart and editing its lines."""

  @staticmethod
  def get_cart():
    """The caller's cart: quantities, unit prices, item count and total.

    Quantities and contents live on the site, so this is a read of that session
    and not of the database. Prices are a snapshot the site forgets on any
    reload, which is why they only become real when an order is submitted.
    """
    return McpAuth.cart().get_info()

  @staticmethod
  def set_cart_quantity(product_id: int, quantity: int):
    """Set one cart line's quantity. At least 1. Persisted server-side."""
    return McpAuth.cart().update_item_quantity(product_id, quantity)

  @staticmethod
  def set_cart_price(product_id: int, price: int):
    """Set one cart line's unit price, in whole dinars. At least 1.

    A snapshot only: the site holds it until something reloads the cart, so
    checkout is what makes it real.
    """
    return McpAuth.cart().update_item_price(product_id, price)

  @staticmethod
  def remove_cart_item(product_id: int):
    """Remove one line from the cart, addressed by product id."""
    return McpAuth.cart().remove_item(product_id)

  @staticmethod
  def tools():
    return (
      CartTools.get_cart,
      CartTools.set_cart_quantity,
      CartTools.set_cart_price,
      CartTools.remove_cart_item,
    )
