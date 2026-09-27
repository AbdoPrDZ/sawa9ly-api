# Architecture

## Shape

Two front ends, one service layer, one HTTP client, one database.

```text
cli/*.py                src/controllers/*.py      ← entry points (argparse, FastAPI)
      \                        /
       \                      /                     both call the same services
        \                    /
     src/services/  ────────────────────────────── domain logic
      Cart, Product      page wrappers over the site
      OrderService       local state machine, submits via Cart
             │
        src/utils/  ────────────────────────────── transport
      Livewire           one user's session; calls the site's Livewire endpoints
      Selector           a page + its selector guide + cached document
             │
        sawa9ly.app
             │
     src/models/  ────────────────────────────── persistence
      SQLAlchemy entities; local mirror of users, keys, catalogue, orders
```

A dependency may point downward only. Services never import controllers or CLI
code; `src/utils` never imports services. `src/models` is the exception — it is
leaf-level and used from both services and controllers.

## Two entry points, one behaviour

The CLI and the API are deliberate mirrors. Every operation exists in both, and
they must not diverge: a change that adds a service method without a CLI command
or a route is incomplete work. `api.md` has the specifics.

The CLI itself has three doors onto one parser — `python main.py`,
`python -m sawa9ly`, and the installed `sawa9ly` console script. All three reach
`cli.app.App.main()`. Only `cli/app.py` builds the parser; the others are
one-line shims, so a new command group needs no change to any of them.

The CLI returns plain dicts and lists and hands them to `Output.render`. It has
no knowledge of tables. The API returns the schemas in `src/schemas.py` and knows
nothing about the CLI. Shared logic belongs in a service, never in an entry
point.

## The per-user client

`Livewire` is the unit of identity and the reason the project is multi-user.

- **`Livewire(username)` is the only form.** A username is required; there is no
  default and no shared no-argument instance. A client *is* an identity, so
  building one always says whose session it drives.
- The API caches one client per username in `src/server.py`, because building one
  may perform a login and that is not something to repeat per request. A CLI run
  is one short-lived process and does not need the cache.

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
| Catalogue, clients, orders | `data/sawa9ly.db` | The local mirror. Authoritative for our own workflow. |
| Parsed page | the `Selector` instance | Cached until `refresh()`. A stale document is the usual cause of "the value did not change". |
| Livewire clients | process memory (`client_cache`) | Rebuilt on restart; harmless, since a client can always log in again. |

## Threading

`requests.Session` is not thread-safe, and FastAPI runs synchronous handlers on
a threadpool. Two concurrent requests for the same user can therefore drive one
session simultaneously.

The project handles this by *not pretending it is safe*: per-user clients narrow
the blast radius to one user's own session, and handlers that do blocking I/O
are declared `def` rather than `async def` so they run in the threadpool instead
of stalling the event loop. Do not add an `async def` handler that performs HTTP,
and do not share one `Livewire` between users to "save a login".
