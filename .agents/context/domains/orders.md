# Orders

An order is prepared locally and submitted later. The whole point is that a
composed order can be reviewed before it becomes a real purchase.

## States

```text
draft ──▶ confirmed ──▶ done
  │           │
  └──▶ cancelled ◀┘
```

| State | Meaning | Editable |
| --- | --- | --- |
| `draft` | being composed locally | yes |
| `confirmed` | accepted by the site; its `origin_id` and `reference` are recorded | no |
| `done` | finished with | no |
| `cancelled` | called off, from a draft or after posting | no |

`cancelled` is terminal and reachable from both `draft` and `confirmed`, because a
draft can be abandoned and a posted order can be called off. It is **not**
reachable from `done`: an order that has run its course is finished rather than
cancelled, and undoing that is an accounting question rather than a state change.

Transitions are otherwise forward-only and skip nothing. There is no path back to
`draft` and no `draft → done`: a caller that wants to change a confirmed order
composes a new one. The transition table lives on `OrderState` as data, and
`can_transition` is the only thing that decides — do not scatter `if state ==`
checks around the code, because they will disagree with each other. The CLI takes
its `state` choices from `OrderState.ALL` for the same reason.

Refusing an edit is a 409 in the API and an `error:` exit in the CLI, and the
message names the state that blocked it.

## The site's order id

`origin_id` is the number the site generated, e.g. `879988`. It is nullable and
distinct from `reference`: the id is an integer, so it can be compared, indexed
and looked up, which is what makes it possible to ask the site about one specific
order later instead of matching on a string.

The id does **not** come back as a bare number. The site's submit returns a
serialised Eloquent model — a list whose second element is
`{'class': 'App\\Models\\Order', 'key': 879988, 's': 'mdl'}` — and the id is its
`key`. `OrderService._origin_id` searches that shape rather than assuming one, and
returns `None` rather than a wrong id, because a wrong one would be stored and
used to ask the site about an order that is not this one.

The page at `/order/{origin_id}` is read by `src/services/order_page.py`; see
`tracking.md` for the job that reconciles an order's state against it.

## Why the state check is inside the transaction

Each mutating operation re-reads the order and re-checks that it is a draft
before writing. Holding a `Order` object across a request and trusting the state
it had when it was loaded would allow an edit to a confirmed order, because nothing
else re-validates. A confirmed order whose lines changed is worse than a
rejected edit: it no longer matches what the site accepted.

## The two product ids

The most consequential detail in this domain.

- `Product.id` — our autoincrement primary key.
- `Product.product_id` — the sawa9ly id, unique, and the id the site and the CLI
  both speak.
- `OrderLine.product_id` — despite the name, a foreign key to the **internal**
  `products.id`.

So the same concept has two values, and which one you have depends on where you
are standing. A path parameter, a CLI argument and an order line all say
"product_id" and can mean different things.

`OrderService` owns the translation in both directions and nothing else should do
it. When talking to the site, resolve through the line's product. When accepting
input, resolve the sawa9ly id to a catalogue row first — and a sawa9ly id that
is not in the catalogue is an error, not a reason to create a line pointing at
nothing.

A line is addressed by product, not by line id, because a product appears at most
once in an order. Adding the same product twice is an update to the existing
line, not a second line.

## Totals

The order total is derived from its lines, never stored, and is recomputed on
read. Quantity and unit price live on the line; the subtotal and the total are
functions of them. A stored total is a value that can disagree with the lines
that justify it.

Prices are integers in the site's currency, and a price below 1 is rejected — the
site's own validation does this, and the refusal is surfaced rather than
swallowed.

## `origin_price` is a snapshot, not a lookup

`OrderLine.origin_price` is the product's own price **as it was when the line
was created**, parsed from the catalogue's display text (`'14,500 دج'`) by
`Product.parse_price` and stored as a number.

It is stored rather than read through `product.price` on demand, because the site
changes prices. Reading the product at display time would rewrite the history of
every order that line belongs to, and the margin an order was built at would stop
being recoverable. `as_dict` reports the stored value; do not "simplify" it into
a join.

**It is set once, when the line is created, and never refreshed.** Toggling a
top-up does not update it — a later purchase of the same product is a different
moment, and belongs in its own order if that moment matters.

Two cases give null rather than a number, and null means *unknown*, not zero:

- the product was not in the catalogue when the line was created, so there was
  no price to read. Scraping the product afterwards does **not** fill it in;
- the product's display text has no number in it — "sur demande", "prix non
  disponible" — so `parse_price` returns None.

Lines that predate the column stay null. Backfilling from today's catalogue would
be a guess about the past and is not done.

`Product.parse_price` disambiguates separators by position, because both
conventions occur: with a comma and a dot present the rightmost is the decimal
point; with one kind, a group of exactly three digits is a thousands separator
and a shorter group is a decimal. Only the whole part is kept — an order line
sells in whole units, and dropping cents beats rounding them into a total.

## Catalogue dependency

Order lines reference the global `products` table, so the catalogue is a shared
dependency and a cascade from it reaches order history. This is worth keeping in
mind before adding any way to delete a saved product.

## What submitting does

`checkout` is the only path from an order to the site, and it drives the site's
own cart rather than posting an order payload — the site has no such endpoint.
The mechanics, and the rules that make it safe to run, are in `checkout.md`.

A successful submit moves the order to `confirmed` and records the site's
reference. Until then the order is entirely local, which is what makes composing
one safe to experiment with.
