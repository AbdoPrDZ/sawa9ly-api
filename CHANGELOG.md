# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version lives in `src/version.py`. Bump it there and add an entry here in
the same change — `setup.py` and the API's advertised version both read that
file, so there is no second place to update.

## [Unreleased]

### Added

- **Landing pages.** A user can write an HTML page per product and publish it at
  `/pages/{public_id}`. `LandingPage` and `PageState` are the entity, a page
  model can only exist for a product — so the dashboard never faces a page with
  nothing behind it — and the project is a deliberate difference from
  `OrderState`, where the site's own wording wins. A published page is served
  under a `Content-Security-Policy: sandbox`, with `allow-scripts` and
  `allow-popups` and no `allow-same-origin`, so page HTML runs without being able
  to reach the API's cookies or its storage. `PageController` mirrors the CLI at
  `/api/v1/pages`; `PublicPageController` serves the page itself and is
  registered last, because it is a catch-all at the site root.
- **`/api/admin/orders`**, listing and fetching any user's orders. It is the one
  route that crosses user boundaries, so it asks for `require_super` rather than
  the usual `require_admin`.
- **A `cancelled` order state**, reachable from `draft` and from `confirmed` and
  terminal once there. A draft can be abandoned and a posted order can be called
  off, so both need a way to say so; `done` deliberately cannot be cancelled,
  because an order that has run its course is finished rather than called off and
  undoing that is an accounting question rather than a state change.
- **`orders.origin_id`**, the order number the site generates (`879988`, say).
  Distinct from `reference`, which was always text: this one is an integer, so it
  can be compared, indexed and looked up, and that is what makes one specific
  order addressable on the site afterwards.
- **`src/services/order_page.py`**, a `Selector` page model for the site's own
  `/order/{origin_id}` page. It reads the order's reference, status, delivery
  details, financial summary and its lines. Each line is recognised by the
  product link it carries, because that link is the only place the sawa9ly product
  id appears on the page; the site's own price for the line is read alongside the
  charged one, which makes it an independent check on `origin_price` rather than
  a copy of what we sent.
- **`src/services/order_sync.py` and a second queue job.** A pass now reconciles
  each posted order's state against the site's, so an order cancelled on the site
  becomes `cancelled` here without anyone retyping it. Only `cancelled` is
  applied — the one state the site has actually been seen to report — and
  anything else, including a move our state machine forbids, is reported as a
  disagreement rather than guessed at, because `cancelled` is terminal and a wrong
  read could not be undone by running the pass again. An order with no
  `origin_id` is skipped: there is no page to read.

### Fixed

- **`_origin_id` reads the shape the site actually returns.** The submit does not
  hand back a number; it returns a serialised Eloquent model, a list whose second
  element is `{'class': 'App\\Models\\Order', 'key': 879988, 's': 'mdl'}`, and the
  id is its `key`. The old code did `str()` on that list, so `reference` held a
  Python repr of a PHP array. The value is now searched for rather than assumed,
  `reference` holds a clean `879988`, and an unrecognised shape yields no id at
  all — a wrong id would be stored and then used to ask the site about an order
  that is not this one.
- **`Cron._report` no longer reports one job by name.** It was hardcoded to
  `tracking`, so the pass line could not have mentioned the orders job even once
  there was one. It now reports whatever the queue is running, and prints
  disagreements under `~` so they are distinguishable from errors.
- **`OrderStateBadge` cannot render a `cancelled` order as `done`.** It fell
  through to the `done` badge for any state it did not recognise, so a cancelled
  order would have been drawn as a successful one. It is a lookup keyed by state
  now, and the CLI takes its `state` choices from `OrderState.ALL` rather than a
  hand-written list that had already drifted out of step with the model.

### Changed

- **Every route moved under `/api`.** This breaks any existing client:
  `/v1/products` is now `/api/v1/products`, `/auth/login` is now
  `/api/auth/login`, `/admin/users` is now `/api/admin/users`, and `/health` and
  `/me` are now `/api/health` and `/api/me`. `API_BASE` is one parent prefix, so
  the outer namespace is written down once and no controller carries it.
- **The dashboard moved from `public/` to `dashboard/`.** `public/` sat next to
  `src/` and `data/`, and Python packaging swept it up; `dashboard/` names what it
  is and keeps its `node_modules` and `dist` in one obvious place. It is still
  served from `dashboard/dist` and still mounted at `/dashboard`.

### Documentation

- The README's project layout, the order state machine, the checkout description
  and the queue section were all describing the previous behaviour. The queue
  section now names both jobs and says what the orders job will and will not do.

## [1.3.0] - 2026-09-27

### Added

- `python main.py router` lists the API's routes — one row per method, with its
  tag and summary, as a table or as JSON with `--json`. It reads the same
  OpenAPI schema `/docs` publishes, so it cannot drift from the documentation.
  It is a developer command, not a domain operation, so there is no service
  behind it and nothing mirrors it in the API.
- `API_GUIDE.md`, a guide for API callers: which credential each route wants,
  what every error code means, and worked workflows. It covers placing an order
  safely, the site's quantity-is-server-side and price-is-not asymmetry, and
  how to be a good guest on a site with no API. The README's route tables stay
  the summary; `/docs` stays the schema reference.

### Fixed

- `AccountsError` is now one of the CLI's expected refusals, so `serve` and
  `router` report a missing super account as `error: ...` with a non-zero exit
  instead of a traceback. It reaches them through `create_app`.

### Changed

- **The machine-facing routes moved under `/v1`.** This breaks any existing API
  client: `/products` is now `/v1/products`, `/cart` is `/v1/cart`, and so on for
  all 19 machine-facing paths. The version prefix is one parent router in
  `create_app`, so `API_PREFIX` is written down once and no controller carries
  it; a `/v2` would be added alongside `/v1`, not in place of it.
- `API_PREFIX` is the wire-format version and is not derived from `VERSION` in
  `src/version.py`; the two move independently.

### Unchanged

- **`/auth/*` and `/admin/*` are deliberately NOT versioned.** They are the
  dashboard's own API and `public/` is their only caller, so there is no second
  consumer to keep compatible. Their paths are unchanged, which is the point:
  moving a private endpoint buys a migration nobody needs.
- `/health` and `/me` also stay at the root. `/health` is what a load balancer or
  container health check points at, and those are configured against a fixed
  path — versioning it would break them silently.
- The dashboard applies the prefix in one place, `urlFor` in
  `public/src/api/client.ts`, so the per-resource api modules stay
  prefix-agnostic. `UNVERSIONED_PREFIXES` there lists the dashboard's own
  endpoints and must be kept in step with the unversioned mounts in
  `create_app`.
- The Vite dev proxy now lists `v1`, `auth`, `admin`, `health` and `me` — and
  versioning retired the old `/products` collision between the API's scrape
  routes and the dashboard's own products page.

### Documentation

- The README now says to restart both the API and the Vite dev server after
  changing routes or `vite.config.ts`. Neither reloads that configuration on
  its own, and a stale process answers with a 404, a 405, or the dashboard's own
  HTML — which reads like a bug in the code you just changed rather than in the
  process you forgot to restart.

## [1.2.0] - 2026-09-27

### Added

- Log lines for the session lifecycle in `src/utils/livewire.py`: which of the
  three outcomes `_build_session` took (stored session reused, stored one no
  longer authenticating, nothing stored), the outcome of a login, and the two
  paths that used to retry silently — a mid-run bounce to the login form and a
  419 CSRF rejection.
- Log lines for Livewire transport in `_dispatch`: one per request, a warning on
  the 419 retry, and an error on a failed response.
- Log lines for the checkout stages in `src/services/cart.py`: the cart start,
  a stop before the order form, the submit, and the quantity stall where the
  server silently refuses to move a line further.
- `src/version.py` as the single source of the version.
- `setup.py`, `MANIFEST.in` and `LICENSE`, so the project can be built and
  installed. Running from a checkout with `python main.py` is unaffected.
- A `sawa9ly` package, so an install can be driven with
  `python -m sawa9ly <command>` or the `sawa9ly` console script. Both reach
  `cli.app.App.main`, the same implementation `python main.py` uses. Installs
  from a clone or straight from the repository URL, and pip supplies the build
  backend itself, so neither `setuptools` nor `wheel` need installing first.
- `.env.example`, documenting all 19 environment variables the project reads so
  a new checkout has a template to copy. `.env` itself stays gitignored.

### Changed

- `src/server.py` reads `API_VERSION` from `src/version.py` instead of
  hardcoding it, so the advertised version and the packaged version cannot
  disagree.

### Removed

- The `old/` directory, the pre-refactor flat implementation. Nothing imported
  it and it was kept only for reference.

## [1.1.0]

The previous release.

Its contents are not reconstructed here: this file starts at 1.2.0, and the
history before it was never written down. Add the details from the release
notes if that history is worth keeping.
