# Catalogue, Prices and Clients

Reference data. None of it is part of an order; all of it is input to one.

## Catalogue

`Product` is a **global** table, not per user, holding the sawa9ly
`product_id` and the information scraped from a product page.

- Saving is an explicit act (`catalogue save`), not a side effect of viewing a
  product. Scraping a page must not write to the database.
- `images`, `figures` and `categories` are stored as JSON text. They are opaque
  lists of strings from the site and nothing queries inside them, so there is no
  case for normalising them into tables.
- **A product has two prices, and they mean different things.** `cost` is the
  site's own price, parsed from the display text and stored as a whole number. It
  is read-only: every scrape overwrites it and no user may set it. `price` is the
  sell price and belongs to the user; it defaults to `cost` the first time the
  product is fetched and is **not** overwritten by a later scrape or tracking
  pass, so a chosen price survives a re-fetch. `margin` is `price - cost`,
  computed on read and never stored — a stored margin is a value that can
  disagree with the two numbers that justify it.
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
they become the product's `cost`, not an order price. What an order sells at is
the `price` or the price set on the line. See `checkout.md`.

## Delivery prices

`DeliveryPrice` is global for the same reason the catalogue is: the site publishes
one price list, so a sync run by one user is read by all of them.

**The key is the site's own wilaya id, and it is a foreign key to `wilayas.id`.**
That is the whole reason the wilayas table exists. The shipping page prints a
wilaya's number *and* its name, but a scraper can only read the number, so without
the table a saved price says `16` and nothing about who that is. It was a bare
integer at first and became a key when the reference data arrived.

Three rules here are the ones a plausible change would break:

- **`available` is a stored value, not an absent row.** The site prints
  `غير متوفر` for a wilaya it does not serve, and that is an answer rather than
  an absence: it is the difference between "no delivery here" and "we do not know
  the price". A row is kept either way, so a wilaya that *becomes* served is an
  update, and the two prices are null while it is not served.
- **A sync updates and inserts; it never deletes.** A wilaya the page no longer
  lists is left alone. The page omitting it is not the site saying it stopped
  delivering there, and turning a scrape that silently matched fewer rows into a
  wipe of good data is the worse of the two mistakes.
- **The office column is found by the label inside it, not by its position.** An
  available card holds `div.w-2/5` twice — the wilaya's name, then the office
  price — so taking the first match reads the name as a price. This is the general
  trap `AGENTS.md` records: count what a selector matched before trusting it.

### Wilayas and communes

`Wilaya` and `Commune` are the reference data the whole delivery side hangs off,
seeded from `src/seeds/wilayas_communes.sql` and never written by the application.
Both use the **site's** ids as their primary key, because those are the numbers the
checkout form is sent — the same reasoning as `Product.product_id`, and the same
mistake as giving them an autoincrement key instead.

**The commune-to-wilaya mapping is the fragile part, and how it was got matters.**
The site has no commune list page and no search, so it cannot be read off a page.
Its commune select is ordered by wilaya, and the block lengths come from a
commune-to-wilaya listing — so the parent is a block's position, not anything
parsed from a name. Joining by transliterating the Arabic was tried and rejected:
Arabic toponyms have several established Latin spellings, so a name match is a
guess with a confidence attached, and **a wrong parent on a commune means an order
that fails at submit.** The block layout is checkable — its per-wilaya counts match
the published figures (Algiers 57, Tizi Ouzou 67, Sétif 60, Tamanrasset 5) — and
the names are not needed for the mapping at all.

There is deliberately **no Latin transliteration column** on either table, for the
same reason. A guessed column is a second answer to "what is this place called"
that nobody can check.

Both tables carry a `server_default` on `created_at` and not only a Python
default, because a raw `INSERT` from the seed does not run Python and the load
fails on a NOT NULL it cannot see a value for.

### Scraping

Unlike the product page, the price list is **static markup**: no wire component
owns it, so there is no `wire:model` or `wire:click` to key on and the guide is
class chains. That makes a re-probe the only defence — if the layout moves, the
scrape either returns fewer cards or returns the wrong numbers, and neither fails
outright. A card with no wilaya number is raised rather than skipped, because a
silently short table looks exactly like wilayas that are simply not served.

The site occasionally prints a price of `0` for a real wilaya, so a zero in the
table is not necessarily a parsing bug — compare it with the page before
concluding either way.

## Clients

A client is a delivery recipient belonging to a user, and its fields are exactly
what the checkout form needs: `full_name`, `phone`, `adresse`, `wilaya_id`,
`commune_id`.

- **There is no `note` on a client, and that was deliberate.** A note belongs to
  the thing it is about, and the two things that carry one — an order and a line
  on it — already do. On a recipient it had nowhere to be shown and nothing to
  tell it apart from the order's own note, so it was a field that could be written
  and never read. It was removed from the model, the schema, the CLI, the MCP tool
  and the dashboard form together; removing it from one of them would have left a
  write that went nowhere.
- `Client.wilaya_id` and `Client.commune_id` are the site's ids, which are now
  `Wilaya.id` and `Commune.id`. They are plain integers rather than foreign keys,
  which is a deliberate inconsistency with `DeliveryPrice.wilaya_id`: a recipient
  is entered before it is necessarily complete, and a null or not-yet-chosen id
  must not stop somebody saving an address. The pair is checked by the site at
  submit, not by us — see the second bullet.

- They exist so an order can be composed without retyping an address, and so the
  CLI and API never handle raw form data.
- **The wilaya and the commune are chosen from the seeded reference data, not
  typed as numbers.** `WilayaCommuneFields` in the dashboard is the whole of that
  UI, and it is one component because the commune list depends on the wilaya:
  changing the wilaya clears the commune, since the site rejects a pair whose
  commune is not in the chosen wilaya. `Client.wilaya_id` and `Client.commune_id`
  are still the site's ids and are still what gets submitted — the selects are a
  way of choosing an id, not a change to what is stored.
- The site requires the wilaya and commune ids as ids, not names. The pairing is
  a site-side constraint: the wilaya determines the valid communes. Storing them
  together invites an inconsistent pair, so they are kept as the site's own
  constraint dictates and validated at submit time rather than guessed at.
- Deleting a client leaves its orders in place with no recipient. An order must
  not disappear because an address book entry was removed; it becomes a draft
  that needs a client before it can be submitted.

## Boundaries

Catalogue, prices and clients are inputs. They do not know about orders, and the checkout
form does not know where its fields came from — it receives a mapping. That is
what allows the same checkout to be driven by a CLI flag, a stored client, or an
API body without special cases.

A price is saved, not looked up per order: the checkout total is built from the
order lines, and what a delivery costs is an input somebody decided earlier, not
something the submit path recomputes.
