# How the site behaves

These were established by probing the live site, and they drive the design:

- **Quantities are server-side; prices are not.** A price only ever lives in
  the Livewire snapshot, so it is gone after any reload. That is why `checkout`
  takes prices and applies them on the way to `submit`, instead of expecting
  `cart set-price` to stick.
- **The order reads quantities from the cart and prices from the component
  state.** Pushing `products_quantity.X` as an `updates` value changes the
  on-screen mirror but not the total — so quantities are applied through the
  `+`/`-` actions (`incrementQuantity`/`decrementQuantity`), one unit per
  request.
- **`?step=2` does nothing.** The checkout step is component state, not a URL
  parameter; a fresh load always mounts at step 1.
- **A component action belongs to the *nearest* `wire:id` ancestor.** The
  add-to-cart button lives on `productaddtocart`, a child of `pages.product`.
  Sending the wrong component returns `500`.
- **Livewire reports validation failures in the snapshot's `memo`,** not as an
  HTTP error, so `checkout` reads them from there.
- **Login is not Livewire.** `/login` is an ordinary Laravel form
  (`POST /login` with `_token`, `email`, `password`), so it is a normal form
  post rather than a `/livewire/update` call.
