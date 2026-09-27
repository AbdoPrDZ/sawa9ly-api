# Domains

Business areas with their own rules. Read the file for the area you are changing;
skip the rest.

| Domain | Covers | Read it when |
| --- | --- | --- |
| `authentication.md` | API keys, per-user sawa9ly sessions, credentials | Adding auth, touching keys, debugging "logged out" or a wrong-user cart |
| `orders.md` | Order lifecycle, state machine, the two product ids | Anything touching orders or order lines |
| `checkout.md` | Driving the site's cart and two-step checkout | Touching cart mutation, prices, or submitting an order |
| `catalogue.md` | Saved product info and delivery clients | Touching products, scraped data, or checkout recipient fields |

## Boundaries

- **Orders** own local intent — what should be ordered, at what quantity and
  price, and in what state. They do not talk to the site directly; they go
  through `Cart`.
- **Checkout** owns the interaction with the site. It knows about components and
  snapshots. It knows nothing about orders.
- **Catalogue** is reference data. Products describe what exists; clients describe
  where to deliver. Both are inputs to an order, never part of one.
- **Authentication** owns identity. Everything downstream takes a `Livewire` and
  does not care where it came from.

The dependency arrow points one way: catalogue → orders → checkout. Nothing in
checkout imports an order, which is what keeps the site's quirks isolated to one
file.
