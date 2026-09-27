# Catalogue and Clients

Reference data. Neither is part of an order; both are inputs to one.

## Catalogue

`Product` is a **global** table, not per user, holding the sawa9ly
`product_id` and the information scraped from a product page.

- Saving is an explicit act (`catalogue save`), not a side effect of viewing a
  product. Scraping a page must not write to the database.
- `images`, `figures` and `categories` are stored as JSON text. They are opaque
  lists of strings from the site and nothing queries inside them, so there is no
  case for normalising them into tables.
- A saved product is the only way an order can reference something, so the
  catalogue must contain the product before an order line can be built for it.
- Order lines cascade from this table. See the hazard noted in `orders.md` before
  adding any way to delete a product.

### Scraping

The guide is scoped because the product page has **four** swipers, and a broad
image selector picks up thumbnails and the customer-photo gallery alongside the
product's own images. The result is a scrape that looks successful and carries the
wrong images. When a scrape changes shape, re-probe and check what was matched
rather than loosening a selector.

Prices scraped from a page are the site's defaults, which carry no commission —
they are not usable as order prices. See `checkout.md`.

## Clients

A client is a delivery recipient belonging to a user, and its fields are exactly
what the checkout form needs: `full_name`, `phone`, `adresse`, `wilaya_id`,
`commune_id`, and an optional `note`.

- They exist so an order can be composed without retyping an address, and so the
  CLI and API never handle raw form data.
- The site requires the wilaya and commune ids as ids, not names. The pairing is
  a site-side constraint: the wilaya determines the valid communes. Storing them
  together invites an inconsistent pair, so they are kept as the site's own
  constraint dictates and validated at submit time rather than guessed at.
- Deleting a client leaves its orders in place with no recipient. An order must
  not disappear because an address book entry was removed; it becomes a draft
  that needs a client before it can be submitted.

## Boundaries

Catalogue and clients are inputs. They do not know about orders, and the checkout
form does not know where its fields came from — it receives a mapping. That is
what allows the same checkout to be driven by a CLI flag, a stored client, or an
API body without special cases.
