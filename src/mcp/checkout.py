"""Ordering the current cart, as an MCP tool.

The shorter way to submit an order: `checkout_order` assembles the cart from a
saved draft order, while this takes the lines and the recipient directly. Both
end at the same place on the site.
"""

from src.mcp.auth import McpAuth


class CheckoutTools:
  """Setting the cart's quantities/prices and submitting the order form."""

  @staticmethod
  def checkout_cart(quantities: dict, prices: dict, client: dict, dry_run: bool = False):
    """Order the current cart: fill the form with `client` and submit it.

    `quantities` and `prices` map product id to quantity and to unit price, and
    are applied before the form is filled — omit a product to leave its line as
    the site already has it.

    `client` is the order form: `full_name`, `phone`, `adresse`, `wilaya_id` and
    `commune_id`, plus an optional `note`. Every field except `note` is required
    by the site.

    **A call with dry_run false places a real order that cannot be cancelled from
    here.** Pass dry_run true to stage the lines and stop before the form, which
    is what to do first whenever the quantities, prices or recipient are
    uncertain. The answer carries `errors` from the site when it refuses.
    """
    return McpAuth.cart().checkout(
      quantities=quantities,
      prices=prices,
      client=client,
      dry_run=dry_run,
    )

  @staticmethod
  def tools():
    return (CheckoutTools.checkout_cart,)
