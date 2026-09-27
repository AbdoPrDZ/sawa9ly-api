# Orders

An order is prepared locally and submitted later. The whole point is that a
composed order can be reviewed before it becomes a real purchase.

## States

```text
draft ──▶ confirmed ──▶ done
```

| State | Meaning | Editable |
| --- | --- | --- |
| `draft` | being composed locally | yes |
| `confirmed` | accepted by the site; its reference is recorded | no |
| `done` | finished with | no |

Transitions are forward-only and skip nothing. There is no path back to `draft`
and no `draft → done`: a caller that wants to change a confirmed order composes a
new one. The transition table lives on `OrderState` as data, and `can_transition`
is the only thing that decides — do not scatter `if state ==` checks around the
code, because they will disagree with each other.

Refusing an edit is a 409 in the API and an `error:` exit in the CLI, and the
message names the state that blocked it.

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
