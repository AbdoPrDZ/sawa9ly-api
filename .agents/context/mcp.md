# MCP

A third front end, alongside the CLI and the HTTP API, over the same services,
served by `python main.py mcp` — which is a command in `cli/mcp.py` and nothing
else: the package builds the server, the command serves it.

Its own process, on its own port (`MCP_HOST`/`MCP_PORT`, default
`127.0.0.1:8001`), with the streamable-HTTP transport at `MCP_PATH`
(`/mcp/`). Not mounted on the FastAPI app and not under `/api`, for the same
reason the credential is separate: a different key on a path that is already
published contract would mean one restart takes both surfaces down.

`MCP_PUBLIC_URL` is a **third** address and the easiest to get wrong. It is what a
client connects to — what the sign-in redirect sends a browser to — and it is
neither the bind address nor the published one. It must be https; a remote
connector refuses plain HTTP.

## Why it is not just another route

An MCP client is a language model, not a script. Four things follow, and they are
the only things that differ from a controller:

- **Authentication is OAuth or a key, resolved per call.** A shell gets
  `--user`; a request gets a bearer token, because one process serves every
  client.
- **Failures are raised, never returned.** A tool that answered `{"error": ...}`
  would be a *successful* call carrying a failure the model has to notice. See
  `errors.py`.
- **The docstring is the interface.** FastMCP derives a tool's input schema from
  its signature and its description from its docstring, so a tool's prose has to
  say what it is *for*.
- **`INSTRUCTIONS` has to stay in step with `TOOL_GROUPS`.** It is text handed to
  a model, and a model told about a tool that is not registered asks for it and
  gets "no such tool" rather than being told there is none.

## The sign-in

Claude's connector flow is OAuth 2.1, and **this project is its own authorization
server**. FastMCP's `OAuthProxy` presents the entire client-facing protocol — the
RFC 8414 and RFC 9728 discovery documents, DCR, PKCE, resource indicators, CIMD,
the short-lived reference JWT — and proxies it to an upstream AS. Every upstream
FastMCP ships is somebody else's (Auth0, WorkOS, Keycloak…). Ours is
`authorization.py`, and it is ours because the project already has what an AS
needs and an IdP does not: a table of users with real passwords on it.

**So signing in is the user lookup.** A hosted IdP hands over a subject like
`auth0|abc123` and leaves the work of mapping it to a sawa9ly user; here the
person types their dashboard password and `User.check_password` resolves them
directly.

The division, worth keeping straight:

| | owns |
| --- | --- |
| `OAuthProxy` (FastMCP) | discovery, DCR, CIMD, PKCE, resource binding, refresh, the token the client holds |
| `authorization.py` | the sign-in page, the password check, the authorization code, the tokens we mint |
| `verifier.py` | checking one of our own tokens |
| `api_keys.py` | the other credential: an `mcp` API key |

Three things about the arrangement that cost time and should not be rediscovered:

- **`resource_base_url` is a base, not the resource.** FastMCP appends
  `mcp_path` to it, so passing the full path yields `.../mcp/mcp/` and *every*
  authorize request is refused as a resource mismatch. Pass the origin.
- **`require_authorization_consent="external"`.** The default shows the proxy's
  own consent page between the person and the login, asking about a decision they
  have already made by typing their password.
- **`verify_token` receives *our* token, not the client's.** The client holds a
  reference JWT whose only real claim is a `jti`; FastMCP resolves that to the
  upstream token and hands us ours. So the verifier is a signature check and a
  claim read — no introspection endpoint and no jti table, despite the reference
  token making it look otherwise.

Tokens are signed and stateless, in the same shape as the dashboard's
(`utils/tokens.py`), with the key in `app_secrets`. **They cannot be revoked
individually** — an hour's life, or rotate the secret for everybody. Deliberate:
a per-token table would be a second answer to "who is signed in" and this project
has one, the `users` table. `typ` is in the payload so an access token and a
refresh token cannot be used for each other.

## The credential

`McpAuth` turns an `AccessToken` into a `User`, and **re-reads it from the
database** rather than trusting the claim — so a deleted account loses access
immediately, not at expiry. Everything after that follows from "the key
identifies the user" exactly as on `/api/v1`: no user in the arguments, one
`Livewire` per user, one cart each.

**Two credentials reach it.** `MultiAuth` takes the proxy and, after it,
`McpApiKeys` — so an OAuth token and an `mcp` API key both arrive as the same
thing and nothing downstream knows which was used.

One library detail worth keeping: the key arrives as `Authorization: Bearer`, not
`X-API-Key`. That is the header OAuth defines and the only one an MCP client
sends, and FastMCP's auth middleware runs *before* any middleware a caller adds —
so normalising the other spelling means wrapping the ASGI app outside what
`run()` builds. Not worth it.

## One divergence from the HTTP API, on purpose

`save_catalogue_product` scrapes through **the caller's own** sawa9ly session.
`/api/v1/catalogue/{id}` scrapes through `User.browsable` — the first user by name
with complete credentials — because that route carries no `Depends` and so knows
no caller. The reasoning inverts here: this call knows whose session it is, so
there is nothing left to borrow one for, and a caller missing their own
credentials is told so by name with the command to fix it rather than being
quietly served by a stranger's session.

The other two catalogue tools are the mirror image of that: the rows belong to no
user, so `list_catalogue` and `get_catalogue_product` call `McpAuth.user()` for no
reason except to require the credential. They do it anyway. A tool surface where
three local-table tools need no key is a surface where nothing does.

## What is and is not a tool

A module exists for every `/api/v1` resource, and **`TOOL_GROUPS` in
`src/mcp/server.py` is the switchboard**: a resource is served when it is in that
tuple and not otherwise. Three are on — products, catalogue, pages, ten tools.
The other six (cart, checkout, clients, orders, telegram, trackers) are written
and commented out, so **the surface does not currently mirror `/api/v1`**.

Turning one on is uncommenting its import and its tuple entry. Nothing else is
missing: the module, `McpAuth` and the per-key ownership scoping are already there.

Cart and orders are the deliberate half to leave off first, because they are the
ones that can spend money. `INSTRUCTIONS` is kept in step with the tuple on
purpose — it is text handed to a language model, and a model told about a tool
that is not registered will ask for it and get "no such tool" rather than being
told plainly that there is none.

**Being off is not the same as being unreachable, and that distinction bit.** With
`CartTools` switched off, `tools/list` still returns `add_product_to_cart` and
`remove_product_from_cart`, because they belong to `ProductsTools` — they are
`/api/v1/products/{id}/cart`, a product operation that happens to touch the cart.
So `INSTRUCTIONS` once claimed "there is no tool that changes a cart", which the
registry contradicted on its very next line. It now says what is actually true:
products can be added and removed, and nothing sets a price, submits, or orders.

The mirroring rule is otherwise unchanged: an operation in one front end and not
the others is unfinished work.

Two things that are HTTP routes are **not** tools whatever the tuple says, for
the reasons `trackers.py` and `telegram.py` state in their own docstrings: the
tracking pass, and polling Telegram. Both are long-lived processes, and one tool
call must not be able to become a loop that outlives it.

## In a container

The `mcp` service in both compose stacks, on the host's loopback at `8001`. The
one image serves it: `command: ["python", "main.py", "mcp"]`.

Two things about it that are not obvious from the service block:

- **It replaces the image's health check rather than disabling it.** The image's
  probe asks for `/docs`, which this container does not serve, so it would report
  permanently unhealthy the way `telegram` and `cron` do. The replacement asserts
  the MCP mount *refuses* a plain `GET` — 401 with a `WWW-Authenticate` challenge,
  or 406 without the `Accept` header it wants. That separates three failures a
  socket check calls identical: refused means the server is down, 404 means
  `MCP_PATH` is wrong. `http.client` rather than `urllib`, because urllib raises on
  a 4xx and inverting that is what keeps the probe to one line.
- **`MCP_PUBLISHED_HOST` is not `MCP_HOST` and not `MCP_PUBLIC_URL`.** Three
  addresses, three questions: what the process binds in there, what Docker
  exposes on the machine, and what a client connects to. `serve` got
  `API_PUBLISHED_HOST` for the same reason.

With sign-in in place, loopback is protecting something slightly different than it
was: not `tools/list` (which now demands a credential like everything else) but
the **discovery documents**, which are readable by anyone who can reach the port.

## Shape

One module per resource, mirroring `src/controllers/`, each a class whose
`tools()` returns its callables. Every method name is unique across the package
and is the tool's public name — FastMCP keys its registry by name, so two `read`
methods in different resources would be one tool.

`TOOL_GROUPS`, at module level in `src/mcp/server.py`, is that list, written
once. Adding a resource means adding a module and one entry, in the order
`create_app` mounts the corresponding controller — and deciding whether it
should be switched on at all, which is a separate question from whether it works.
