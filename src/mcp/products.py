"""Product pages, as MCP tools.

The three operations the HTTP API exposes under `/api/v1/products`, against the
same service. No logic is reimplemented here: a tool is a route with a different
envelope.
"""

from src.mcp.auth import McpAuth
from src.services import Product as ProductPage


class ProductsTools:
  """Reading a product page and moving it in and out of the cart."""

  @staticmethod
  def get_product(product_id: int):
    """Scrape a sawa9ly.app product page: title, price, images, description,
    figures and availability.

    `product_id` is the number in the product's URL on the site. This reads the
    live page rather than the saved catalogue, so it always costs one request to
    sawa9ly.app.
    """
    product = ProductPage(product_id, McpAuth.client())

    return {"product_id": product.product_id, **product.get_info()}

  @staticmethod
  def add_product_to_cart(product_id: int):
    """Add a product to the caller's cart, and return the cart afterwards.

    Goes through the product page rather than the cart page, because that is the
    only way the site lets a product enter a cart.
    """
    return ProductPage(product_id, McpAuth.client()).add_to_cart()

  @staticmethod
  def remove_product_from_cart(product_id: int):
    """Remove a product from the caller's cart, and return the cart afterwards."""
    return ProductPage(product_id, McpAuth.client()).remove_from_cart()

  @staticmethod
  def tools():
    """Every tool this group contributes, in the order they are declared."""
    return (
      ProductsTools.get_product,
      ProductsTools.add_product_to_cart,
      ProductsTools.remove_product_from_cart,
    )
