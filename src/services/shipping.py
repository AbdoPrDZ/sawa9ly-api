"""Shipping page service: what the site charges to deliver to each wilaya."""

import re

from pyquery import PyQuery as pq

from src.models import Product
from src.utils import BASE_URL, Selector
from src.utils.livewire import LivewireError

#: Printed in place of both prices for a wilaya the site does not deliver to.
#: Compared against one cell rather than the whole page, because it is ordinary
#: Arabic text that could just as well appear in a notice.
UNAVAILABLE_LABEL = "غير متوفر"

#: Introduces the office-collection price inside a card. It is what identifies
#: that column: an available card holds `div.w-2/5` twice, so the office price
#: cannot be told from the name by position.
OFFICE_LABEL = "مكتب التوصيل"

#: The card's own wilaya number. Zero padded on some cards and not on others —
#: `01 - أدرار` next to `50 - برج باجي مختار` — so it is read as digits and
#: converted, never sliced to a fixed width.
LEADING_ID = re.compile(r"^(\d+)")


class Shipping(Selector):
  """The delivery price list published on `/shipping`.

  One card per wilaya: the number and the name on the left, the two prices on
  the right — or, for a wilaya the site does not deliver to, a single
  `غير متوفر` and nothing else.

  Prices are handed back as numbers rather than as the text the site displays,
  so nothing downstream has to know that `'1000 دج'` is a price. `Product.parse_price`
  does the parsing because it already knows how this site writes numbers, and a
  second parser would be a second answer to the same question.

  **The selectors are class chains, because nothing else is available.** The price
  list is static markup: the only wire components on the page are the search box,
  the cart icon, the footer and the notifications, and none of them owns a price.
  So there is no `wire:model` or `wire:click` to key on, and what the guide holds
  is the structure the markup itself offers. Count what each selector matched per
  card before trusting it — that is how the office column is found at all.
  """

  guide = {
    # Scoped to the grid that holds the cards. The card's own classes are generic
    # enough to match a promo banner or a footer block if the site adds one, and
    # the direct-child relation is what says "this grid's children are the list".
    "cards": "div.grid.grid-cols-1.lg\\:grid-cols-3 > div.border.flex.justify-between.items-center",
    # The number and the name, plus on an available card the office address and
    # the delivery time. Never parsed for a price.
    "identity": "div.w-2\\/5",
    "price": "div.w-1\\/5",
    "office": "div.w-2\\/5",
    # Printed where both prices would be, so it is only ever present on a card
    # the site does not deliver to.
    "unavailable": "div.w-3\\/5",
  }

  def __init__(self, client):
    self.url = f"{BASE_URL}/shipping"
    super().__init__(client)

  def get_prices(self):
    """One row per wilaya, in the shape `DeliveryPrice.sync` takes.

    A card with no price on it still yields a row, with both prices None, rather
    than being left out. The wilaya is the thing that exists; whether the site
    currently delivers to it is a value on the row.
    """
    return [self._row(pq(card)) for card in self.select("cards")]

  def _row(self, card):
    identity = self._part(card, "identity")
    number = LEADING_ID.match(identity)

    if number is None:
      # Raised rather than skipped. A card that cannot be attributed to a wilaya
      # is either a selector that has stopped matching or a page that changed
      # shape, and both mean the table would be quietly short a row — which
      # looks exactly like a wilaya that simply is not served.
      raise LivewireError(
        "A card on the shipping page has no wilaya number, so its price cannot "
        f"be attributed to one. It starts: {identity[:60]!r}. Re-probe "
        f"{self.url} before trusting the saved prices."
      )

    return {
      "wilaya_id": int(number.group(1)),
      "available": UNAVAILABLE_LABEL not in self._part(card, "unavailable"),
      "price": Product.parse_price(self._part(card, "price")),
      "office_price": Product.parse_price(self._office_column(card)),
    }

  def _office_column(self, card):
    """The office price's cell, or None when the card has no office price.

    An available card holds `div.w-2/5` twice — the name, then the office
    column — and they are told apart by the label inside the second one. Taking
    the first match instead would read the wilaya's name as its office price,
    which `parse_price` turns into a number rather than rejecting.
    """
    for column in card(self.get_selector("office")):
      text = Shipping._flatten(column)

      if OFFICE_LABEL in text:
        return text

    return None

  def _part(self, card, path):
    """The text of the first match for a guide selector inside one card."""
    found = card(self.get_selector(path))
    return Shipping._flatten(found.eq(0)) if len(found) else ""

  @staticmethod
  def _flatten(node):
    """An element's text with its whitespace collapsed.

    Takes either a pyquery object or the raw element it hands out when iterated —
    the two differ in whether `.text` is a method or a property, and the callers
    here hold both, so the wrapping happens once in this method.
    """
    return " ".join(pq(node).text().split())