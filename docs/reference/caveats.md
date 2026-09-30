# Caveats

- `cart set-price` and the price part of a cart update do not persist — the
  value is only visible in the response for that request. Use `checkout`.
- Quantities are applied server-side and **persist even if the checkout later
  fails**, so a rejected checkout can still leave quantities changed. Use
  `--dry-run` to stage without submitting (quantities are still applied).
- `checkout` with a complete, valid `client` **places a real order** that cannot
  be cancelled from here. Test with incomplete `client` data to exercise the
  flow without ordering.
- Selectors are tied to the site's markup and Tailwind classes; the long
  `nth-child` chains in `Product.guide` will break if the theme is redeployed.
