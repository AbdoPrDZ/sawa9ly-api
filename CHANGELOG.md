# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version lives in `src/version.py`. Bump it there and add an entry here in
the same change — `setup.py` and the API's advertised version both read that
file, so there is no second place to update.

## [Unreleased]

### Fixed — an occupied port says so, instead of raising `Errno 10048`

- `main.py serve` and `main.py mcp` now check the port before they build
  anything. A bind failure otherwise arrived from uvicorn as
  `OSError: [Errno 10048] ... only one usage of each socket address` *after* a
  twenty-line startup banner — which names neither what is holding the port nor
  what to do about it, which on a machine where an IDE has quietly taken 8001 is
  the entire problem.
- It now says which address, how to find the holder (`netstat -ano | findstr` on
  Windows, `lsof` elsewhere) and which flag changes it. `EACCES` — a privileged
  port — gets its own sentence rather than being lumped in.

### Added — signing in to the MCP server, with no third-party identity provider

- **The MCP server is its own OAuth authorization server.** Claude's connector
  flow is OAuth 2.1 with CIMD, and FastMCP's `OAuthProxy` presents that whole
  client-facing protocol — the RFC 8414 and RFC 9728 discovery documents, dynamic
  client registration, PKCE, resource binding, Claude's published client identity,
  the short-lived reference token — and proxies it to an upstream AS. Every
  upstream FastMCP ships is somebody else's: Auth0, WorkOS, Keycloak, Google.

  This project is the upstream. It has to be, because it already has what an AS
  needs and an IdP does not: a table of users with real passwords on it. A hosted
  provider hands back a subject like `auth0|abc123` and leaves the work of mapping
  it to a sawa9ly account; here the person types their **dashboard** username and
  password, `User.check_password` resolves them, and the connector gets a token
  naming them. Signing in *is* the lookup, so there is no identity-mapping problem
  and no third party between you and your own account.
  - Connect with **Sign in now** and leave the OAuth client on the default, *Use
    Claude's published identity*. Both work.
  - The sign-in page is served from the MCP server itself, sandboxed and
    `no-store`. A wrong password says nothing about which half was wrong, so the
    endpoint is not a way to enumerate accounts.
- **Tokens are signed and stateless**, in the same shape as the dashboard's but
  with a different issuer — so one verifier can never accept the other's tokens.
  An access token lasts an hour and is refreshed silently; a refresh token cannot
  be used as a bearer credential, and an access token cannot mint one.
  **They cannot be revoked individually**: an hour's life, or rotate the
  `mcp_token` row in `app_secrets` and sign in again. Deliberate — a per-token
  table would be a second answer to "who is signed in" and the project already
  has one, the `users` table. The dashboard's own session tokens work the same way,
  for twelve hours.
- **`MCP_PUBLIC_URL`**, the address a *client* connects to. A third address,
  alongside the two Docker already has: not `MCP_HOST` (what the process binds
  inside the container) and not `MCP_PUBLISHED_HOST` (what Docker exposes on the
  machine). It is what the sign-in redirect sends a browser to, and it must be
  https — a remote connector refuses plain HTTP. `main.py mcp` prints the URL to
  paste and says which of these is wrong.
- **Both credentials still work.** An OAuth access token *or* an API key of type
  `mcp`, through `MultiAuth`, resolving to the same per-user session and the same
  cart. A scripted client keeps working.

### Changed — an MCP API key is now sent as a bearer credential

- **`Authorization: Bearer sk_...`, not `X-API-Key`.** OAuth defines one header for
  a bearer token and every MCP client sends that one. FastMCP's auth middleware
  runs before any middleware a caller adds, so a request carrying only
  `X-API-Key` is refused before a normaliser could rewrite it — accepting both
  would mean wrapping the ASGI app outside what `run()` builds, which is a lot of
  fragile arithmetic to preserve a second spelling of the same credential. The
  HTTP API's `X-API-Key` is unaffected.

### Changed — `tools/list` is no longer open, which changes what loopback protects

- With auth on the whole endpoint, a request with no credentials is refused
  before it reaches a tool, so the list of 10 tool names and descriptions is no
  longer readable by anyone who can reach the port. What *is* still open is the
  pair of discovery documents under `/.well-known/`, which name the server's
  endpoints. `MCP_HOST` still defaults to loopback and the compose stack still
  publishes on `127.0.0.1`; it is protecting a smaller thing than it was.
- **The `mcp` container's health check now asserts a 401**, not a 406. The mount
  refuses a plain `GET` because the endpoint demands a bearer token, and that
  refusal is the healthy answer. 406 is still accepted for the same endpoint
  reached without the `Accept` header it wants. Both separate a server that is
  down from an `MCP_PATH` that is wrong, where a socket check calls both success.

### Added — an MCP server, and a second kind of API key

- **An MCP server**, so an AI agent can drive the client with the same operations
  a script uses. FastMCP, in `src/mcp/`, run by `python main.py mcp` — a third
  front end beside the CLI and the HTTP API, over the same services. It is its
  own process on its own port (`MCP_HOST`/`MCP_PORT`/`MCP_PATH`, default
  `127.0.0.1:8001/mcp/`) rather than a route on the FastAPI app, because it holds
  a different credential and one restart should not take both surfaces down.
- **10 tools, covering three resources**: products, the saved catalogue, and
  landing pages. A module per resource is written for all nine, and
  `TOOL_GROUPS` in `src/mcp/server.py` is where a resource is switched on — the
  rest are present but not registered yet, so **the MCP surface does not yet
  mirror `/api/v1`**. Adding one is uncommenting its import and its tuple entry.
  A route added without a tool remains unfinished work; a tool added without one
  is not.
  - What that means in practice: an agent can look at a product, keep a local
    catalogue of what it saw, and write landing pages — but it cannot drive a
    cart or place an order yet, so the irreversible half of the surface is
    deliberately absent.
- **A key is now one of two kinds.** `api_keys.type` is `api` or `mcp`, and a key
  is accepted by exactly one of them: the HTTP API refuses an `mcp` key and the
  MCP server refuses an `api` one. They are separate because they are handed to
  different things — an API key is typed into a script by its owner, while an
  `mcp` key is typed into an AI agent's client configuration and from there lands
  in transcripts and tool arguments. One key accepted by both would put
  `/api/admin` behind a token that is by construction read by a language model.
  A key of the wrong type is reported as *unknown*, so a refused key cannot
  confirm that somebody else's credential exists.
  - Issue one with `apikey create --type mcp`, `POST /api/keys`, or the
    dashboard's issue-key form, which gained an api/mcp picker.
  - The column has a `server_default` of `api`, so every key that existed before
    it is an `api` key and keeps working.
- **An `mcp` service in both compose stacks**, on `127.0.0.1:8001`. Its health
  check replaces the image's `/docs` probe rather than being disabled: it asserts
  the MCP mount answers a `GET` with 406 Not Acceptable, which separates a server
  that is down from an `MCP_PATH` that is wrong, where a socket check would call
  both success.
- **`API_PUBLISHED_HOST` and `MCP_PUBLISHED_HOST`**, each defaulting to
  `127.0.0.1`, so the address Docker exposes on the machine is a setting rather
  than a line of compose file someone has to edit. They are deliberately separate
  from `API_HOST`/`MCP_HOST`, which are what the process binds inside the
  container and must stay `0.0.0.0` — the loopback interface in there belongs to
  the container.
- **`LandingPageService.describe(page)`**, so the landing-page shape — the joined
  sawa9ly id and title — has one home rather than one per front end. The
  controller's `_out` now delegates to it.

`tools/list` is **not** authenticated: anything that can reach the port sees every
tool name and description without presenting a key. Every tool *call* needs one.
This is why `MCP_HOST` defaults to loopback and the compose stack publishes it on
the host's loopback only.

### Added — landing pages, order state, and the `/api` namespace

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
- **Every route moved under `/api`.** This breaks any existing client:
  `/v1/products` is now `/api/v1/products`, `/auth/login` is now
  `/api/auth/login`, `/admin/users` is now `/api/admin/users`, and `/health` and
  `/me` are now `/api/health` and `/api/me`. `API_BASE` is one parent prefix, so
  the outer namespace is written down once and no controller carries it.
- **The dashboard moved from `public/` to `dashboard/`.** `public/` sat next to
  `src/` and `data/`, and Python packaging swept it up; `dashboard/` names what it
  is and keeps its `node_modules` and `dist` in one obvious place. It is still
  served from `dashboard/dist` and still mounted at `/dashboard`.

### Added — Telegram notifications

- **Telegram notifications, and linking a user to a chat.** A user issues a
  single-use code from their profile, opens the `t.me` link carrying it, and
  `python main.py telegram listen` records the chat against their account. The
  code is 10 characters, valid 15 minutes, and stored only as a SHA-256 digest,
  so it is shown once and cannot be read back out of the database.

  The code is what makes the binding mean anything: a Telegram chat id is a
  number the API hands out and anyone can read off a screenshot, whereas a code
  proves both that the sender can post in that chat and that they were allowed to
  claim that account. It travels as a deep link rather than being typed, so
  nothing can be mistyped and it is never exposed in a group chat.

  A private chat with the bot needs no setup. A private channel works too, with
  the bot added as an admin; **a group is refused**, and the rule is in the
  database rather than only in the UI. One chat belongs to one account via
  `UNIQUE(chat_id)`, so two users cannot claim the same channel, and issuing a new
  link never unlinks the chat a user already had.

  Updates are received by **long polling, not a webhook**, so this needs no public
  address, no certificate and no domain — it dials Telegram and Telegram never
  dials back. Telegram holds undelivered updates for 24 hours, so a code sent while
  the listener was down is delivered when it next starts. Only one listener may
  poll a token, enforced by `data/telegram.lock`, because Telegram's answer to a
  second poller is a 409 on every poll and that reads like a network fault rather
  than what it is.

  Optional throughout: with no `TELEGRAM_BOT_TOKEN` set the whole integration is
  off and nothing else changes.

- `python main.py telegram test [--user]`, which sends a test message to a linked
  chat, and `POST /api/v1/telegram/test` with a **Send a test message** button on
  the dashboard's Telegram card. It is how a link is checked without opening a
  terminal, and it exits non-zero when it cannot send, so it is usable as a check
  in a script. 404 when no chat is linked, 502 when Telegram itself refuses.
  `TelegramService.send_to_user` is the one place a message goes to a user.
- `telegram_chat_id` in the admin users view, so a super can tell somebody which
  chat they linked.

### Added — notifications

- **A notification when a watched product changes.** The queue already diffed each
  scrape against the stored row, so the previous value was already in hand. A
  change to `available` or to `price` now raises a notification for everyone
  watching that product.

  A notification is a **record**, not a call, and it holds no recipient: one
  change is one `notifications` row however many people watch the product, and the
  fan-out is a row per person in `notification_deliveries` under a
  `UNIQUE(notification_id, user_id)`. That is what stops one event becoming one
  message per watcher, and it is what lets a send that failed for one person be
  retried without resending to everybody it already reached. Creating the row
  *is* the sending.

  **One message per product per fetch, however many fields moved.** A scrape that
  finds the price and the stock both different is one thing that happened once; an
  earlier version raised one event per field and sent two messages about a single
  change, which is the sort of thing that gets a bot muted. Each change now gets
  its own line inside one message. The kind is `product.changed` — one kind for
  the event, not one per field, because "which fields moved" belongs in the body
  where a reader wants it.

  A **price** change is compared on the **numbers** the two display texts parse
  to, never on the text: the site may print `16,000 دج` one minute and
  `16.000 دج` the next, and diffing the raw string would put a message in
  somebody's chat about a comma. Each line says which way it moved and from what,
  because a new number with no "was" beside it is not news anybody can act on. A
  price appearing or disappearing — "sur demande" and back — is its own case
  rather than a silent null.

  Which tracked fields are worth a message is `NOTIFIABLE_FIELDS` in
  `src/services/notifications.py`, written out and not derived: a title or
  description change is recorded in the diff and reported by the pass, but whether
  that is worth interrupting somebody for is a judgement this code should not make
  on its own.

  Every outcome is kept. A chat that was blocked is a delivery with
  `send_error` set and `sent_at` null, and a user with no linked chat is a
  delivery saying so — never a silent gap. A delivery failure is reported in the
  pass's `notify_errors` and deliberately **not** in `errors`, so `cron run` does
  not exit non-zero because one person muted a bot: the scan did its job, and a
  queue that cries wolf trains you to ignore its exit code.

  Retry is bounded twice, both because a notification is only true for as long as
  it was noticed: by age (an hour, so a chat unblocked over lunch still gets it),
  and by cause — a delivery that found no linked chat is not retried at all,
  because that user had not opted in when the event happened.

### Fixed

- **A pasted code was checked leniently and then hashed strictly.** The code
  matcher stripped quotes, backticks and spaces to decide whether a message held
  a code, but handed back the original text — so a user who copied theirs out of
  a backticked page was told their code was unknown while looking at it. The
  matcher now returns the cleaned code or None, and `hash_code` normalises too, so
  the thing that decides and the thing that hands it on cannot disagree.
  Backticks, quotes, stray spaces, lowercase and a stray hyphen all work now; a
  sentence containing a code is still refused, because stripping the words out
  would leave a 10-character match for the wrong reason.
- **The dashboard pointed at the one button that cannot work.** The page a
  `t.me` link opens has two: "Start Bot", which hands off to Telegram's app via the
  `tg://` scheme and silently does nothing on a computer with no app installed,
  and "Open in Web", which carries the same code in a `tgaddr` fragment and works
  with none. The instruction named the second rather than saying "open this link",
  and still offers the code as a message for the same reason.
- **The bot asked to be sent the link.** `/start` with no code replied "Send me
  the link from your dashboard", which is wrong — a bot cannot do anything with a
  `t.me` URL. It now asks for the 10-character code, which is also what makes the
  no-app-installed case recoverable.
- `Cron._Lock` gained a path, a staleness and a message so the Telegram listener
  could reuse it. A staleness of 0 was meant to mean "never take over" but
  `age <= 0` is false for a lock written a moment ago, so a second listener was
  let in. Zero now means never, explicitly.
- **Comparing a stored timestamp to `utcnow()` raised.** The columns are plain
  `DateTime` and SQLite keeps no timezone, so every value read back is naive while
  `utcnow()` is aware, and the comparison raises rather than answering. This had
  already bitten the Telegram code once and been patched privately there; the
  fix now lives in `src/db.py` as `as_utc`, next to `utcnow`, because every
  column in this project has the same problem.

### Changed

- **No role can set another user's sawa9ly credentials any more, including a
  super.** This is a breaking change to the API: `sawa9ly_email` and
  `sawa9ly_password` are gone from `AdminUserIn`, and
  `POST`/`PATCH /api/admin/users*` no longer accept them. `sawa9ly_email` is also
  gone from `AdminUserOut` — an admin can see that a user is set up, not the
  address they used. The fields are the user's own, entered on their profile, and
  an admin who could type them in could also act as that user on sawa9ly.
  `Accounts.may_set_site_credentials` was removed rather than left as a door
  nothing opens. The CLI's `user add --email --password` is unchanged and remains
  the operator's bootstrap path.

  The dashboard's create and edit user forms no longer render the sawa9ly fields
  at any role, and the users table shows "set" / "not set" in place of the email.

### Fixed

- `_origin_id` reads the shape the site actually returns. The submit does not
  hand back a number; it returns a serialised Eloquent model, a list whose second
  element is `{'class': 'App\\Models\\Order', 'key': 879988, 's': 'mdl'}`, and the
  id is its `key`. The old code did `str()` on that list, so `reference` held a
  Python repr of a PHP array. The value is now searched for rather than assumed,
  `reference` holds a clean `879988`, and an unrecognised shape yields no id at
  all — a wrong id would be stored and then used to ask the site about an order
  that is not this one.
- `Cron._report` no longer reports one job by name. It was hardcoded to
  `tracking`, so the pass line could not have mentioned the orders job even once
  there was one. It now reports whatever the queue is running, and prints
  disagreements under `~` so they are distinguishable from errors.
- `OrderStateBadge` cannot render a `cancelled` order as `done`. It fell through
  to the `done` badge for any state it did not recognise, so a cancelled order
  would have been drawn as a successful one. It is a lookup keyed by state now,
  and the CLI takes its `state` choices from `OrderState.ALL` rather than a
  hand-written list that had already drifted out of step with the model.
- `API_GUIDE.md` documented routes that no longer exist. Every path in it predated
  the `/api` namespace, so all twelve references would have produced a 404. The
  versioning section now explains both prefixes and why `/dashboard` and
  `/pages/{public_id}` sit outside `/api`.
- A 404 from the catalogue named a path that no longer existed. It now names the
  action instead, since any absolute path written into a message is one that can
  go stale.
- `Cron._Lock` is parameterised by path, staleness and message, so the Telegram
  listener reuses it instead of carrying a second copy. The queue's own behaviour
  is unchanged.

### Security

- The Telegram bot token is a standing leak risk: the Bot API puts it in the URL
  of every call, and `requests`/`urllib3` quote that URL in their errors. The
  project's `SecretFilter` does not cover it — it redacts a record only when the
  message contains a word like `token` or `secret`, and a real token contains
  neither, and it only clears `record.args` so a token interpolated into
  `record.msg` survives. `src/utils/telegram.py` therefore keeps the token in one
  private attribute, strips it from everything leaving the module, and has a
  `__repr__` that cannot leak it. Verified against the real error paths.

### Documentation

- The README's project layout, the order state machine, the checkout description
  and the queue section were all describing the previous behaviour. The queue
  section now names both jobs and says what the orders job will and will not do,
  and a new section covers linking a chat, the listener, and why no ngrok,
  DDNS or domain is needed.

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
