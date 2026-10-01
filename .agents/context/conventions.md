# Conventions

The rules live in `AGENTS.md` and are injected every session. This file records
the *patterns that exist in the code* and — more importantly — where the code
knowingly departs from its own stated rules, so a newcomer does not either copy a
deviation or "fix" it by accident.

## The shape of each layer

- **ORM entities** (`src/models/`) are declarative classes whose queries are
  classmethods, so an entity is the only place that knows its own table:
  `User.get_or_create`, `ApiKey.find`, `Order.all`, `Product.save`. Instances
  hold behaviour that needs state; the class holds lookups.
- **Page services** (`src/services/`) extend `Selector` and own a URL plus a
  `guide`. `Cart` and `Product` are thin over the site; `OrderService` is the
  exception — it is pure local domain logic that *uses* `Cart` to talk to the
  site, and it is the only service that takes a database session.
- **Controllers** (`src/controllers/`) own an `APIRouter` and register handlers in
  the class body. They translate HTTP to a service call and back, and hold no
  business logic. **One controller per resource**, so admin users and admin API
  keys are two controllers even though both live under `/api/admin`.
- **MCP tools** (`src/mcp/`) are the same shape with a different envelope:
  **one module per resource**, a class of `@staticmethod` tools, and a `tools()`
  returning them. Every method name is unique across the package and is the
  tool's public name, because FastMCP keys its registry by name and two `read`
  methods in different resources would be one tool. The docstring is the tool
  description, so it says what the tool is *for* — see `mcp.md`.
- **MCP credentials** are `TokenVerifier`s on the server's `MultiAuth`, one class
  per credential: `verifier.McpTokens` for a signed access token,
  `api_keys.McpApiKeys` for an API key. `auth.McpAuth` sits above both and turns
  an `AccessToken` into a `User`, re-reading it from the database rather than
  trusting the claim. The OAuth server itself is `authorization.py` plus
  `handlers.py` — the tokens and the markup in one, the request handling in the
  other, because "what a valid request looks like" is a different question from
  "what does one issue".
- **Auth utilities** (`src/utils/`) are split by concern: `passwords.py` holds
  `Passwords`, `tokens.py` holds `Token`. They have no dependency on each other.
  The MCP tokens in `src/mcp/authorization.py` are deliberately *not* in
  `tokens.py`: a different issuer, a different payload and a different lifetime,
  and one verifier must never accept the other's tokens.
- **Domain services** (`src/services/`) are split by what they know, not by
  feature area: `tracking.py` knows about products and diffs, `cron.py` knows
  about timing and locking and calls the former through a job registry. A
  scheduler that understood products would be two reasons to change in one file.
- **CLI groups** (`cli/`) each expose `register(parser, default_user)` and
  `dispatch(args)`. `App.GROUPS` lists them; `App._handles` maps a command name to
  its owner. A group that reaches `src.server` must import it **inside**
  `dispatch`: `cli/app.py` imports every group when it builds the parser, and
  importing `src.server` runs `create_app()`, so a module-level import would make
  every command need a database. `cli/router.py` is the example.
- **Request plumbing** hangs off `Dependencies`, so a controller's signature
  documents its own requirements. The MCP equivalent is `McpAuth`, which hangs the
  same three things off one namespace: `user()`, `client()` and `cart()`.

## Adding a feature, in order

1. Business logic → a service method (or a new service).
2. Database entity, if state is needed → `src/models/`.
3. CLI command → the owning group in `cli/`, or a new `cli/` module added to
   `App.GROUPS` **and** `_handles`.
4. API route → the owning controller, plus a schema in `src/schemas.py`, plus a
   router include in `create_app` if it is a new controller.
5. MCP tool → the owning module in `src/mcp/`, plus an entry in
   `TOOL_GROUPS` if it is a new resource — and a decision about whether to switch
   it on, which is separate from whether it works. A docstring, not a summary: it
   is the tool's description.
6. Tests are manual: exercise the CLI, then the route, then the tool.

The failure mode to avoid is step 3 or 4 alone. All three front ends are supposed
to expose the same operations.

## Environment variables

Every variable is declared in `src/config.py` and read through a `Config`
method. **No other module calls `os.getenv`.** A new setting is a new attribute
plus a documented method there, not a new `os.getenv` in the module that happens
to need it.

The same applies to the default value: a default belongs in `Config`, and there
is exactly one source of it. `Config.DEFAULT_USER` and a `DEFAULT_USERNAME` in
`livewire.py` holding the same `"local"` is the duplication that this rule
prevents.

## Output

All CLI printing goes through `Output.render` in `cli/output.py`. It decides
between a table and a key/value block from the shape of the result, caps cell
width, collapses a column of nested records to a count, and aligns sibling maps
(the cart's quantities and prices) into one table. `--json` bypasses all of it
and returns the raw structure.

This matters because the table output is lossy on purpose: `order list` shows a
line count, `--json order list` returns the full lines. A change that needs full
data in the table should change the renderer, not start printing from a
command.

## Known departures from `AGENTS.md`

`AGENTS.md` says not to add module-level functions. The rule is followed in
`cli/`, `src/models/`, `src/controllers/` and the service classes, but these
modules still have module-level functions, and they predate the rule:

- `src/db.py` — `utcnow`, `database_url`, `init_db`, `session_scope` and the
  private engine helpers. Module-level because they *are* the infrastructure
  and are imported by name across the project.
- `src/utils/livewire.py` — `default_username`, `ensure_db`, `login`,
  `load_session`, `save_session`, `cookie_string` and private helpers. The
  `Livewire` class itself is the important part; these support it.
- `src/utils/__init__.py` — `parse_cookie`, plus `BASE_URL` and `COOKIE_DOMAIN`.
- `src/server.py` — `create_app` and `_mount_dashboard`. `create_app` is a
  conventional app factory; the server module is the one place that composes the
  application. (It also used to hold `client_cache`, which moved to
  `src/utils/client_cache.py` when the MCP server needed the same cache and
  importing `src.server` to reach it would have run `create_app`.)
- `src/services/cart.py` — module-level private helpers (`_item_ids`,
  `_present_quantities`, `_as_int_map`, `_validate`, `_checkout_result`).

Treat these as grandfathered. **New code does not add to them.** Moving one of
these into a class is a reasonable cleanup, but it is a refactor to be done on
purpose, not as a side effect of another change.

## Selectors

`Selector.guide` is a nested dict addressed by dotted paths, which is what makes a
selector a value that can be inspected and reused. Two site-specific findings
that the rules in `AGENTS.md` generalise:

- The product page has **four** swipers. A broad image selector picks up
  thumbnails and the customer-photo gallery alongside the product's own images,
  so the guide is scoped and the count of matched elements is worth checking
  before trusting a scrape.
- Several cart selectors are only correct for a specific cart or product
  ordering, which is why a selector that suddenly stops matching should be
  re-probed rather than patched.

## Where the site is actually driven

`Cart` talks to a single component named `panier` on `/panier`. It resolves that
component by name via `find_component`, then uses the `Livewire` verbs —
`call` for component actions, `update` for state pushes — and reads results back
through `component_data`, which parses the snapshot. A component action must be
addressed to the component that *owns* the element, and validation failures come
back inside the snapshot's `memo` with a 200. `domains/checkout.md` records what
that means for the checkout flow specifically.
