"""Product page model."""

from pyquery import PyQuery as pq

from src.utils import BASE_URL, Selector
from src.utils.livewire import LivewireError

AVAILABLE_LABEL = 'الكمية متوفرة'

REMOVE_FROM_CART = '[wire\\:click="removeFromCart"]'

ALREADY_IN_CART = "Product is already in the cart"
NOT_IN_CART = "Product is not in the cart"
UNAVAILABLE = "Product is not available for purchase"


class Product(Selector):

  guide = {
    "title": "#product-title",
    "images": ".bigImageSwiper .swiper-slide img",
    "availability": "body > div:nth-child(2) > section > div.md\\:grid.md\\:grid-cols-4 > div:nth-child(1) > div > div.pt-1.mb-2 > span",
    "description": "#product-description",
    "figures": "#product-description figure img",
    "price": "body > div:nth-child(2) > section > div.md\\:grid.md\\:grid-cols-4 > div:nth-child(1) > div > div.flex.flex-col.space-y-2.text-xl > div.flex.justify-around.items-center.border-b > div.text-center > div",
    "categories": "body > div:nth-child(2) > section > div.md\\:grid.md\\:grid-cols-4 > div:nth-child(1) > div > div.flex.flex-col.space-y-2.text-xl > div.pt-3.pb-4.border-b.mt-3.text-center.text-sm > a",
    "add_to_cart": "body > div:nth-child(2) > section > div.md\\:grid.md\\:grid-cols-4 > div:nth-child(1) > div > section > div > button.bg-yellow-400.text-black.py-3.text-xs.md\\:text-sm.font-bold.w-3\\/6.block.text-center.rounded"
  }

  def __init__(self, product_id, client):
    self.product_id = int(product_id)
    self.url = f"{BASE_URL}/product/{self.product_id}"
    super().__init__(client)

  def get_info(self):
    """Scrape the product page."""
    return {
      'title': self.select('title').text(),
      'availability': self.select('availability').text().strip().lower() == AVAILABLE_LABEL,
      'images': self.select('images').map(lambda i, el: pq(el).attr('src')),
      'description': self.select('description').text(),
      'figures': self.select('figures').map(lambda i, el: pq(el).attr('src')),
      'price': self.select('price').text(),
      'categories': self.select('categories').map(lambda i, el: pq(el).text().strip()),
    }

  def add_to_cart(self):
    """Add this product to the cart.

    Raises:
        LivewireError: If the button is gone (already in the cart or
            unavailable) or the call fails.
    """
    self.refresh()

    buttons = self.select('add_to_cart')
    if not len(buttons):
      raise LivewireError(
        ALREADY_IN_CART if len(self.doc(REMOVE_FROM_CART)) else UNAVAILABLE
      )

    return self._button_action(buttons)

  def remove_from_cart(self):
    """Remove this product from the cart.

    Raises:
        LivewireError: If the product is not in the cart or the call fails.
    """
    self.refresh()

    buttons = self.doc(REMOVE_FROM_CART)
    if not len(buttons):
      raise LivewireError(NOT_IN_CART)

    return self._button_action(buttons)

  def _button_action(self, buttons):
    button = buttons.eq(0)
    component = self.client.owning_component(button)

    result = self.client.call(self.html, component, button.attr('wire:click'), referer=self.url)
    data = self.client.component_data(result)

    return {
      'product_id': self.product_id,
      'in_cart': data.get('product_in_cart', False),
    }
