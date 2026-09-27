# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version lives in `src/version.py`. Bump it there and add an entry here in
the same change — `setup.py` and the API's advertised version both read that
file, so there is no second place to update.

## [Unreleased]

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
