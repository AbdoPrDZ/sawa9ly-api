# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version lives in `src/version.py`. Bump it there and add an entry here in
the same change — `setup.py` and the API's advertised version both read that
file, so there is no second place to update.

## [Unreleased]

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
  `cli.app.App.main`, the same implementation `python main.py` uses.

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
