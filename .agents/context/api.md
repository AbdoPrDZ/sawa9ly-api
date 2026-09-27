# HTTP API

FastAPI, assembled in `src/server.py`. Run it with `python main.py serve` or
`uvicorn src.server:app`. Interactive docs are served at `/docs`.

## Authentication

Every route except `/health` requires an API key, presented as `X-API-Key` or
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
`/auth/login` and receives a signed, expiring token, sent back as
`Authorization: Bearer`. The two share a header name but nothing else — they are
separate dependencies with separate token formats, and neither is accepted where
the other is expected.

## The mirroring rule

The API mirrors the CLI. An operation that exists in one and not the other is
incomplete work.

Adding a route means all of:

1. a method on the owning service,
2. a handler on the owning controller class,
3. a body/response model in `src/schemas.py`,
4. a router include in `create_app` — **only** if the controller is new.

Schemas are the contract; clients depend on the exact shape, so widen by adding
an optional field rather than renaming or removing one. The response for an order
keeps its `lines` in full at the API level, even though the CLI table shows a
count — the CLI's compactness is a rendering choice and must not leak into the
schema.

## Resources

Grouped by the page they drive, which is also how the controllers are split:
products, cart, checkout, catalogue, clients, orders, plus `/health` and `/me`.
Orders are the deepest: an order has lines, and a line is addressed by product
id rather than by line id, because a product appears at most once in an order.

Self-service lives on `/auth/me/*` and is available to **any** signed-in user,
whatever their role — changing your own password or your own sawa9ly credentials
should never need an administrator. Editing *somebody else's* account is
`/admin`, and is super-only.

Ordering of concerns when adding a route: resolve auth, resolve the user, get the
`Livewire` through the dependency, then call a service. Do not construct a
`Livewire` in a handler, and do not import `src.server`'s client cache from
anywhere else — going through `Dependencies` keeps one construction path.

## Who may do what

The matrix lives in `src/services/accounts.py`, not in the handlers, so a route
never re-derives it:

| actor \ action | own profile | add a user | edit a user | delete a user | set another's sawa9ly credentials |
| --- | --- | --- | --- | --- | --- |
| `super` | yes | yes | yes | yes | yes |
| `admin` | yes | yes | no | no | no |
| `user` | yes | no | no | no | no |

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
