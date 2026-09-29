# HTTP API

FastAPI, assembled in `src/server.py`. Run it with `python main.py serve` or
`uvicorn src.server:app`. Interactive docs are served at `/docs`.

## The namespace: `/api`

Every route this application serves sits under **`API_BASE`**, written down once
in `src/server.py`. It exists so the API owns a known namespace and the site root
can be handed to the public pages without either of them moving later. The
dashboard is under `/dashboard`, so `/` currently answers 404 with a pointer to
it.

The prefix is applied where the routers are mounted, not in the controllers, so no
controller knows where it lives.

## The `/api/v1` version prefix

`API_PREFIX` covers the **machine-facing** routes only — the ones a caller reaches
with an API key. They nest under one versioned parent router in `create_app`, so
`API_PREFIX` is written down exactly once. A `/v2` is a second parent beside the
first, not an edit to the block, so `/api/v1` clients keep working.

`API_PREFIX` is the version of the **wire format**, and is deliberately not
derived from `VERSION` in `src/version.py`. That one is the application's
version; they move independently.

Three groups sit under `/api` but carry **no version**, and the reason differs in
each case:

- **`/api/auth` and `/api/admin`** — the dashboard's own API. `dashboard/` is the
  only caller, so there is no second consumer to keep compatible. They are mounted
  through a second router that takes `API_BASE` but not `API_PREFIX`, which is why
  their paths read as `/api/auth/login` and `/api/admin/users`.
- **`/api/health`** — what a load balancer or container health check points at, and
  those are configured against a fixed path. Versioning it breaks them silently,
  so it is declared inline on the app rather than through either router.
- **`/api/me`** — the meta route that echoes back who a key belongs to.

The split follows the credential, not the resource: `require_admin` and
`get_token_user` mean dashboard-only, `get_current_user` means machine-facing,
and `get_any_user` (trackers) counts as machine-facing because it also accepts an
API key.

Adding a machine route means: pick the controller, register the path relative to
the resource, and **do not** add `/api` or `/api/v1` — the parent applies them.
Adding a dashboard route means the same.

`python main.py router` prints the whole table, one row per method, read from the
same OpenAPI schema `/docs` serves — so it cannot disagree with the
documentation. It reports method, path, tag and summary, and deliberately not
authentication: the routes authenticate through `Depends`, which leaves no
security scheme in the schema, so deriving "needs an API key" would mean a second
source that could contradict the dependency.

## Authentication

Every route except `/api/health` requires an API key, presented as `X-API-Key` or
`Authorization: Bearer <key>`. `Dependencies.get_current_user` resolves it and
returns the `User`.

Two things follow from "the key identifies the user", and both are load-bearing:

1. **There is no user id in the request.** A route never takes a user; it uses
   the authenticated one. A path parameter cannot override it.
2. **Each key gets that user's own `Livewire`**, so the caller sees their own
   cart and their own site session. Two keys never share a cart. This is why
   `Dependencies.get_client` exists and why the client is cached per username.

Failure is 401 with a message that says what to do. An unknown key and a revoked
key are distinguished, because the fix differs.

The dashboard uses a different credential: it posts a username and password to
`/api/auth/login` and receives a signed, expiring token, sent back as
`Authorization: Bearer`. The two share a header name but nothing else — separate
dependencies, separate token formats. `get_current_user` accepts only an API key;
`get_any_user` accepts either, and is used on the `/api/v1` routes a machine and the
browser both drive (`/api/v1/trackers`, `/api/v1/orders`, `/api/v1/clients`,
`/api/v1/pages`). Every other `/api/v1` route stays API-key only, because only
the API key identifies a user for a resource the dashboard does not own.

## The mirroring rule

The API mirrors the CLI. An operation that exists in one and not the other is
incomplete work.

Adding a route means all of:

1. a method on the owning service,
2. a handler on the owning controller class,
3. a body/response model in `src/schemas.py`,
4. a router include in `create_app` — **only** if the controller is new.

**A missing include is silent, not a 404.** The dashboard shell is served from a
catch-all `@app.get("/{path:path}")`, so a request for an API path that was never
registered comes back as `index.html` with a **200**. Anything asking for JSON
then gets a web page and no error. When a new route behaves as though it does not
exist, check the include first, and check that the server was restarted —
`Config.reload()` defaults to **False**, so `python main.py serve` keeps running
the code it started with and ignores Python edits until you stop and start it.
`API_RELOAD=1` turns on the reloader.

Schemas are the contract; clients depend on the exact shape, so widen by adding
an optional field rather than renaming or removing one. The response for an order
keeps its `lines` in full at the API level, even though the CLI table shows a
count — the CLI's compactness is a rendering choice and must not leak into the
schema.

## Resources

Grouped by the page they drive, which is also how the controllers are split:
products, cart, checkout, catalogue, clients, orders, trackers, plus the
unversioned `/api/health` and `/api/me`. Orders are the deepest: an order has lines, and
a line is addressed by product id rather than by line id, because a product
appears at most once in an order.

**Orders have two read surfaces, and they answer different questions.**
`/api/v1/orders` is "my orders" — caller-scoped, API key *or* dashboard token, and it
stays that way for a `super` too. `/api/admin/orders` is "everybody's orders" — super
only, dashboard token only, so the one route that crosses user boundaries is not
reachable by any API key. Keeping them apart is deliberate: widening `/api/v1/orders`
to list all users would hand that to every machine caller in the installation.
`AdminOrdersController` is a separate controller for that reason, and
`require_super` is the dependency that guards it.

Self-service lives on `/api/auth/me/*` and is available to **any** signed-in user,
whatever their role — changing your own password or your own sawa9ly credentials
should never need an administrator. Editing *somebody else's* account is
`/api/admin`, and is super-only.

Ordering of concerns when adding a route: resolve auth, resolve the user, get the
`Livewire` through the dependency, then call a service. Do not construct a
`Livewire` in a handler, and do not import `src.server`'s client cache from
anywhere else — going through `Dependencies` keeps one construction path.

## Who may do what

The matrix lives in `src/services/accounts.py`, not in the handlers, so a route
never re-derives it:

| actor \ action | own profile | add a user | edit a user | delete a user | set another's sawa9ly credentials | see all users' orders |
| --- | --- | --- | --- | --- | --- | --- |
| `super` | yes | yes | yes | yes | yes | yes |
| `admin` | yes | yes | no | no | no | no |
| `user` | yes | no | no | no | no | no |

Plus three rules that are structural rather than per-role:

- `super` is never assignable from the dashboard, by anyone.
- Nobody may change or delete a `super` account from the dashboard at all.
- Nobody may change their own role or delete their own account.

An administrator can therefore *add* a user, but that user starts with no site
credentials and sets their own — which is why the create form hides those fields
for a non-super. The UI hides or disables controls from `can_be_managed` and
`is_admin` rather than letting a request fail with a 403, but the server check is
the real one.

## Status codes

- 400/422 for a malformed or missing body field.
- 401 for a missing, unknown, revoked or expired key.
- 404 for an id that does not exist, or that exists but belongs to another user.
  Do not distinguish the two; that would confirm the row exists.
- 409 when the request is well-formed but the domain forbids it — editing an
  order that is no longer a draft, or a quantity below one.
- 502 when the site failed or returned something unusable. This is the "the site
  broke" case and must be distinguishable from 409.

`OrderError` carries the domain refusals and maps to 409; anything unexpected
from the site layer surfaces as 502. `LivewireError` carries transport and
validation problems from the site.
