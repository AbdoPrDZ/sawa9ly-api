# The Python API

## Python API

```python
from src.services import Cart, OrderService, Product
from src.db import session_scope

product = Product(5663)
product.get_info()          # title, availability, images, description, figures, price, categories
product.add_to_cart()       # {'product_id': 5663, 'in_cart': True}
product.remove_from_cart()  # {'product_id': 5663, 'in_cart': False}

cart = Cart()
cart.get_info()             # {'quantities': {...}, 'prices': {...}, 'count': 2, 'total': 19000}
cart.update_item_quantity(5663, 3)
cart.update_item_price(5663, 16000)
cart.remove_item(5663)
```

Each model takes an optional `client` — a `Livewire` for a specific user — so
you can drive more than one account at once. Without one they use the default
(CLI) user.

```python
from src.utils import Livewire

alice = Cart(client=Livewire("alice"))
bob = Cart(client=Livewire("bob"))
```

Mutations reload the page; call `.refresh()` to force a re-read.

## Checkout

```python
cart.checkout(
  quantities={'5663': 2},              # {product_id: qty}
  prices={'5663': 16000, '5724': 5000},  # {product_id: unit price}
  client={                             # order form
    'full_name': 'Jane Doe',
    'phone': '0555000000',
    'adresse': '1 Rue ...',
    'wilaya_id': 16,
    'commune_id': 1,
    'note': '',                        # optional
  },
  dry_run=False,
)
```

Returns:

```python
{
  'success': False,
  'order': None,
  'step': 2,
  'total': 37000,
  'errors': {'phone': ['حقل رقم الهاتف مطلوب.']},
}
```

Checkout is two steps on the site, and this reproduces both:

1. **Cart** → set quantities and prices, then `next_step`
2. **Form** → `full_name`, `phone`, `adresse`, `wilaya_id`, `note`, then
   `commune_id`, then `submit`

The form is Livewire component state, not a plain HTML form, so its fields are
pushed as component updates rather than typed into the page.

Required form fields: `full_name`, `phone`, `adresse`, `wilaya_id`,
`commune_id`. `note` is optional. Missing fields come back in `errors` and
nothing is ordered.

`wilaya_id` drives the `commune_id` options, so it is always sent in an earlier
dispatch than `commune_id`. Sending them together can submit a commune that is
not valid for the wilaya.

## Minimum commission

The site refuses to advance past the cart unless the order commission is at
least **5% of the total**. The default prices give zero commission, so
`next_step` rejects them:

```python
{'step': 1, 'errors': {'total_commission': ['الحد الأدنى للعمولة هو 5٪']}}
```

Supply prices high enough and the flow proceeds. `checkout` returns this in
`errors` rather than raising.
