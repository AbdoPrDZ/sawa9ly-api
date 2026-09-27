# Project Context

Knowledge layer for the sawa9ly client. It exists so an agent can work on this
project without re-deriving the site behaviour, the data model or the layering
from scratch.

## How to use it

1. Read this file.
2. Read `config.md` — it decides how you may write to the context.
3. Read `structure.md` — it says which file owns which knowledge.
4. Read only the files your task touches, then verify against the source.

**Context is derived knowledge, never authority.** If it disagrees with the
code, the code is right: correct the context and continue. Never edit source to
match stale context.

## Reading by task

| Task | Read |
| --- | --- |
| Touching cart or checkout logic | `domains/checkout.md`, `workflows.md` |
| Touching orders | `domains/orders.md`, `database.md` |
| Touching auth, keys, or sessions | `domains/authentication.md`, `database.md` |
| Touching products, catalogue, or clients | `domains/catalogue.md` |
| Adding a CLI group or API route | `api.md`, `conventions.md`, `architecture.md` |
| Adding or changing a table | `database.md`, `domains/orders.md` |
| Changing how the site is driven | `domains/checkout.md` first — it records the site rules that are easy to break |
| Changing tracking, the queue, or the scheduler | `tracking.md` |
| Unsure where something belongs | `structure.md` |

## The project in one paragraph

A Python client and HTTP API for `sawa9ly.app`, an Algerian dropshipping site.
There is no official API, so the client drives the site's Livewire components
directly. It scrapes product pages, maintains a cart, and places orders. State
that the site owns (carts, sessions) is mirrored locally in SQLite so an order
can be prepared and reviewed before anything is submitted. Two front ends — an
`argparse` CLI and a FastAPI server — sit on one service layer, and both are
multi-user: every user has their own sawa9ly session and therefore their own
cart. An admin dashboard in `public/` manages users, roles and API keys.

## Current state

- Python 3.14, `requirements.txt` is unpinned. No test suite, no linter, no CI.
- Verification is manual against the live site.
- Every environment variable is declared in `src/config.py`; nothing else in
  the project reads `os.environ`.
- **There is no default user.** Every command that acts for an account requires
  `--user`, and `Livewire` requires a username.
- `data/sawa9ly.db` is a real, gitignored SQLite file. `create_all` builds it and
  will not migrate it — delete it to rebuild.
- The version lives in `src/version.py` and nowhere else. `setup.py` and the
  API's advertised version both read that file.
