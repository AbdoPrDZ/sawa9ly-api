# Workflows

Multi-step flows that cross layers. The rules that constrain each step live in
`domains/`; this file is the shape of the sequence and where it breaks.

## Session bootstrap

Triggered whenever a client needs to be authenticated, and lazily — nothing logs
in at import time.

1. A `Livewire` is built **for a named user**, with no default. It loads that
   user's session from `settings`, scoping each cookie to the `sawa9ly.app` apex
   domain.
2. A cheap authenticated page is requested to check the session. A redirect to
   `/login` means it is dead.
3. If dead, or if the mid-run request bounces to `/login`, the client logs in with
   that user's stored sawa9ly credentials and rewrites the row.
4. The retry is invisible to callers: a session that expires *during* a run is
   refreshed and the request replayed.

A user with no credentials recorded cannot get past step 3, and the error names
the command that records them. There is no environment fallback, so the only way
to become able to sign in is to give a user its own credentials. See
`domains/authentication.md`.

## Reading a page

`Selector` loads lazily and caches the document. A service reads from `doc`,
which triggers the load on first access. **After any mutation, the cached document
is stale** — this is the single most common cause of a change appearing not to
have worked. `refresh()` re-reads; most mutating methods already do it.

Scraping returns whatever the guide selects, so a selector that matches more than
it intended produces extra keys rather than an error. Check what was matched.

## Cart mutation

Two different mechanisms, because the site treats quantities and prices
differently. This is site behaviour, not a design choice — see
`domains/checkout.md`.

- **Quantity** — the server owns it. Set it with the component's
  `incrementQuantity` / `decrementQuantity` actions, computed as a delta from the
  current value, looping one unit at a time. A push through `updates` only moves
  the on-screen mirror and never reaches the order.
- **Price** — the component owns it. Push it with `update`. It is never persisted,
  so a price is only good for the request that set it.

Consequence for tests and for ordering: a quantity change survives a reload and a
failed checkout, a price does not. Leave the cart as you found it.

## Cart → order

The site's cart is not a reliable staging area for a composed order, so
`OrderService.checkout` reconciles rather than assumes.

1. Read the site's cart and work out the difference: items the order does not
   want are removed, items it wants are set to the order's quantity.
2. Push every line's price, because it does not persist, and call `next_step`.
3. Push the client fields — `commune_id` in its own dispatch *after* the one
   carrying `wilaya_id`, because the wilaya drives the commune options.
4. Push `commune_id` and call `submit`, then read the result out of the response.

With `dry_run` every step runs except the submit, which is how the flow is
verified without placing an order. Note that dry-run still mutates the site's
cart, so the cart must be restored afterwards.

## Order lifecycle

Entirely local until the submit.

```text
draft ──▶ confirmed ──▶ done
```

`draft` is the only editable state. `confirmed` means the order was accepted by
the site and its reference was recorded; `done` is bookkeeping. Transitions are
forward-only and skip nothing — a client cannot re-open a confirmed order, and
deleting a line is a draft-only operation.

Every mutating method re-checks that the order is still a draft *inside* the
transaction, so a refusal cannot be raced past by holding a stale object.

## Adding an operation

The order matters, because each layer depends on the one before it: service
method, then entity if new state is needed, then schema, then controller, then
CLI group. Then add the router include if the controller is new. A change that
stops after the service is invisible to both users of the project, which is the
usual way this codebase drifts.
