# Architecture

## Shape

Three front ends, one service layer, one HTTP client, one database.

```text
cli/*.py    src/controllers/*.py    src/mcp/*.py    ← entry points
  argparse    FastAPI                 FastMCP
      \            |                     /
       \           |                    /              all call the same services
        \          |                   /
      src/services/  ────────────────────────────── domain logic
       Cart, Product      page wrappers over the site
       OrderService       local state machine, submits via Cart
              │
         src/utils/  ────────────────────────────── transport
       Livewire           one user's session; calls the site's Livewire endpoints
       Selector           a page + its selector guide + cached document
       ClientCache        one Livewire per username, per process
              │
         sawa9ly.app
              │
      src/models/  ────────────────────────────── persistence
       SQLAlchemy entities; local mirror of users, keys, catalogue, orders
```

A dependency may point downward only. Services never import controllers, CLI or
MCP code; `src/utils` never imports services. `src/models` is the exception — it is
leaf-level and used from both services and controllers.

Two consequences of the entry points being peers rather than layers: one belongs to
everybody (a described shape, or a shared cache) and cannot sit in any one of them
without the other two importing sideways. `ClientCache` in `src/utils` and
`LandingPageService.describe` are those two cases; both were single-purpose
helpers in one front end until a second one needed them.

## Three entry points, one behaviour

The CLI, the API and the MCP server are deliberate mirrors. Every operation
exists in all three, and they must not diverge: a change that adds a service
method without a CLI command, a route or a tool is incomplete work. `api.md` has
the specifics for the first two, `mcp.md` the third.

The CLI itself has three doors onto one parser — `python main.py`,
`python -m sawa9ly`, and the installed `sawa9ly` console script. All three reach
`cli.app.App.main()`. Only `cli/app.py` builds the parser; the others are
one-line shims, so a new command group needs no change to any of them.

Each front end returns plain dicts and lists to its own renderer: the CLI to
`Output.render`, the API the schemas in `src/schemas.py`, the MCP server straight
to the client. None of them knows about the others. Shared logic belongs in a
service, never in an entry point.

## The per-user client

`Livewire` is the unit of identity and the reason the project is multi-user.

- **`Livewire(username)` is the only form.** A username is required; there is no
  default and no shared no-argument instance. A client *is* an identity, so
  building one always says whose session it drives.
- The API and the MCP server both cache one client per username, in
  `ClientCache`, because building one may perform a login and that is not
  something to repeat per call. A CLI run is one short-lived process and does not
  need the cache.

Two consequences that are easy to get wrong:

1. **A cart is not global.** It lives inside the site's session, so it belongs to
   a `Livewire`, which belongs to a user. Passing the wrong client silently
   operates on someone else's cart.
2. **Page services require a client.** `Cart(client)` and
   `Product(product_id, client)` have no default and `Selector` raises if given
   none, because a page reached without an identity would have to guess whose
   session it is reading.

## State, and where each kind lives

Knowing which store owns a value prevents the classic bug of fixing one and
reading another.

| State | Owner | Notes |
| --- | --- | --- |
| Sawa9ly session | site, mirrored in `settings` | The site is the source of truth; the row is a cache that is re-established by logging in. |
| Cart contents and quantities | site | Never mirrored. Read it, do not assume it. |
| Cart prices | site, in-memory only | Livewire component state; gone on any reload. |
| Catalogue, clients, orders | `database/sawa9ly.db` | The local mirror. Authoritative for our own workflow. |
| Parsed page | the `Selector` instance | Cached until `refresh()`. A stale document is the usual cause of "the value did not change". |
| Livewire clients | process memory (`ClientCache`) | Rebuilt on restart; harmless, since a client can always log in again. Per process, so the API and the MCP server each keep their own. |

## Threading

`requests.Session` is not thread-safe, and FastAPI runs synchronous handlers on
a threadpool. Two concurrent requests for the same user can therefore drive one
session simultaneously.

The project handles this by *not pretending it is safe*: per-user clients narrow
the blast radius to one user's own session, and handlers that do blocking I/O
are declared `def` rather than `async def` so they run in the threadpool instead
of stalling the event loop. Do not add an `async def` handler that performs HTTP,
and do not share one `Livewire` between users to "save a login".

The MCP server is the same trade in a different runtime. FastMCP runs a `def` tool
in a worker thread by default, which is exactly the FastAPI arrangement, so the
note above applies to it unchanged. The two servers are separate processes, so
their `ClientCache` instances are separate too — one user's site session exists
once per front end, not once per installation.
