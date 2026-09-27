# Cart and Checkout

Everything here is a property of the sawa9ly site, established by probing it
rather than from documentation. They look like bugs. They are not. Do not
"simplify" any of them without re-testing against the live site.

## The site has no order API

Ordering means driving the site's own cart and its two-step checkout as a user
would. There is no endpoint that accepts an order, so the flow is: make the
cart match, advance, fill the form, submit. Anything that tries to shortcut this
is guessing at markup that may change.

## Quantities are server-side; prices are not

The single most important asymmetry in the project.

- **Quantities live in the site's cart**, so they are read from the server. Set
  them with the component's `incrementQuantity` / `decrementQuantity` actions,
  as a delta from the current value, one unit per request. Pushing
  `products_quantity` as an `updates` value moves the on-screen mirror only — the
  order total does not change, and the change is lost on reload.
- **Prices live in the Livewire component state**, so they must be pushed with
  `update` to take effect, and they never persist. A price is valid only for the
  request that set it.

Two operational consequences:

1. A price set by a command is not there when the next command runs. Anything
   that needs a price on an order must set it again on the way to submitting.
2. Quantities persist through a failed checkout. A rejected or dry-run checkout
   can still leave the site's cart changed, so **leave the cart as you found it**
   — put the quantities back when you are done testing.

## Components, not URLs

- The cart is one Livewire component, `panier`, on `/panier`. Find it by name.
- **A component action belongs to the component that owns the element.** pyquery's
  `parents()` is ordered outermost-first, so the intuitive `eq(0)` picks the wrong
  one and the request returns 500. `Livewire.owning_component` exists for this.
- **`?step=2` does nothing.** The checkout step is component state, not a URL
  parameter, so a fresh load always mounts at step 1. Do not try to bookmark or
  reload into a later step.
- The product page nests the add-to-cart component inside the page component.
  Sending the page component's id for an add-to-cart action fails the same way.

## Validation arrives inside a 200

Livewire reports validation failures in the snapshot's `memo`, not as an HTTP
error. A 200 from a checkout step means the request was *received*, not that it
was *accepted*. Every step that can fail must therefore read the result and
surface `errors`.

This is why `checkout` returns `errors` rather than raising for a rejected form:
the site declining a form is a normal outcome to report, not an exception.

## The commission floor

The site refuses to advance past the cart unless the order commission is at least
**5% of the total**, and reports it in `errors`. Prices taken from the site
default to zero commission, so a checkout that only sets quantities stalls at
step 1 with a message about a minimum commission.

This is the site's price model, not a validation bug: the price is a commission
and it has to cover the cost of the drop. Set prices high enough and the flow
proceeds. The threshold is enforced site-side; the client does not duplicate it,
it surfaces what the site said.

## The form

The checkout form is not filled by typing into the DOM. Its fields are Livewire
component state, so each step pushes them as an `updates` value and the component
re-renders. Reading `#orderForm` off the page and posting it would bypass the
component entirely and submit nothing.

Required: `full_name`, `phone`, `adresse`, `wilaya_id`, `commune_id`. `note` is
optional. Fields absent from the client mapping are simply not pushed, and the
site rejects the submit.

The sequence is three dispatches, not two, and the split is not cosmetic:

1. **items** — set quantities, refresh, push the prices, and call `next_step`.
2. **client** — push every field *except* `commune_id`.
3. **submit** — push `commune_id`, then call `submit`.

- **`wilaya_id` goes in dispatch 2, `commune_id` in dispatch 3** — a dispatch
  after the one that sets the wilaya. The wilaya determines which communes are
  offered, so sending them together can submit a commune that is not valid for
  the wilaya. This split is the reason the form is two dispatches.
- `next_step` is a component action, not a URL. `?step=2` does nothing, so there
  is no way to bookmark into the form step.
- The step is read back from the response after `next_step` rather than assumed.
  If it did not become 2, the flow returns the site's reason and stops.

## Testing without ordering

- `dry_run=True` runs every step except the submit. It is the default way to
  verify, and it does not place an order — but it does leave the cart staged, so
  restore the quantities afterwards.
- Alternatively submit with the required client fields omitted. The site refuses
  in `errors` and no order exists.
- **Never** submit a complete, valid client during a test. A real order cannot be
  cancelled from here, and the project has no way to undo it.
