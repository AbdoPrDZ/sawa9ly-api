# Storefront

A public, per-user store: a directory at `/`, a store at `/stores/{slug}`, a
default product page with an order form, and an authored landing page at
`/pages/{public_id}` when the owner has written one.

It is the only surface this project serves that is **open** — no API key, no
dashboard token. That is the whole point, and it is the source of every rule
below.

## What a store is

A store belongs to a `User` and is made of the user's **landing pages**: the
products a store carries are exactly the products that user has written a page
for (see `catalogue.md` and `dashboard.md`). There is no separate "store
product" table and no product ownership on the global catalogue.

A user has a store only when **both** names are set:

- `store_slug` — the URL segment. Unique (a unique index), lowercase, digits and
  single hyphens. It is the key: a store is looked up by it, and the order form
  posts it. **Renaming it breaks every existing link to the store.**
- `store_name` — the display name. Free text, shown to visitors, **not** unique
  and never used as a key. Two stores may share one.
- `store_logo` — optional, stored as a base64 data URI (see
  `src/utils/store_logo.py`). No file storage exists in this project; the logo
  lives in the row.

Clearing the slug clears the store. A half-filled pair is refused rather than
stored, because a store with no URL is not a store.

## The routes

All server-rendered HTML, no JavaScript, all `include_in_schema=False`:

- `GET /` — the directory: a card per store, display name and logo.
- `GET /stores/{slug}` — the store's products as cards, with a `?q=` search.
- `GET /stores/{slug}/{product_id}` — **redirects** to `/pages/{public_id}` when
  the owner has a published page for that product, otherwise renders the
  generated default product page.
- `POST /stores/{slug}/{product_id}/order` — the checkout form's target.

## The public order is the dangerous operation

Everything unusual here exists because of it.

- **It runs as the store's owner**, through that owner's single sawa9ly session
  and cart — the visitor has no account. Two visitors ordering at once would
  drive one cart together, so `Storefront.place_order` takes a **lock per owner**.
- **It is irreversible.** The order is real on sawa9ly and cannot be cancelled
  from this project. So the controller **throttles** it (per IP and per store)
  and uses a **honeypot**: a hidden field a bot fills, whose presence answers
  with the success page and places nothing.
- **The form is offered only when the order can actually be placed** — the owner
  has sawa9ly credentials and the product has a sell price. Otherwise the page
  says so and shows no form. The POST checks the same thing and refuses.
- **A store may only sell its own products.** `product_for_store` requires a
  landing page, so a POST naming any other catalogue product is a 404.
- **The form carries no price and no quantity.** One unit at the product's sell
  price, read from the server. A page a visitor can edit must never decide what
  an order costs.

The order is **stored locally first**: a `Client` from the submitted details, a
draft `Order`, and a line, then submitted through `OrderService.checkout`, so it
appears in the owner's dashboard with the address to fulfil it from. A **new
`Client` row is created per order** — never matched by name — because reusing one
would let a later order rewrite an earlier order's address.

`cost` and `margin` are **never rendered**. The public page shows the sell price
only; what the owner pays sawa9ly is their business.

## Sandbox and why `allow-forms`

These pages share an origin with the dashboard, which keeps its login token in
`localStorage`. So every storefront page is sent
`Content-Security-Policy: sandbox allow-forms`: an opaque origin with no script,
which cannot reach the dashboard, while still letting the checkout form submit.
The bare `sandbox` an authored page gets forbids forms, which is why this one
adds an allowance and nothing else.

The storefront's own markup is escaped in `src/services/storefront_pages.py` and
is the only place it is built. The **authored** page at `/pages/{public_id}` is
different: it is the owner's HTML, served verbatim under the plain `sandbox`, and
the storefront links to it rather than copying it in.

Usernames are never shown. The directory and store show the display name; the
URL shows the slug; the account behind a store is not public.

## Boundaries

The storefront reads the catalogue and writes orders. It does not own either:
`Storefront` resolves a store and its products, then hands off to `OrderService`
for the order itself. Nothing here changes what an order means, and nothing in
`orders.md`, `checkout.md` or `catalogue.md` knows the storefront exists beyond
`LandingPage` being where a store's products come from.
