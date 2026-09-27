# Context Structure

The contract for this project's `.agents/context/`. It defines which files exist,
what each owns, and when a file comes into being. Content changes do not alter
this file; only a change in organisation does.

## Design Constraints

- **No inventories.** No per-class, per-function, per-endpoint or per-column
  listings. The source is the inventory; this layer is the reasoning.
- **No duplication with `AGENTS.md`.** `AGENTS.md` holds *rules the agent obeys*
  and is injected into every session. This layer holds *knowledge about the
  project* and is read on demand. When a fact could live in either, `AGENTS.md`
  wins if it is phrased as an instruction, this layer wins if it is knowledge.
- **No generic framework documentation.** Record how *this* project uses
  SQLAlchemy/FastAPI/Livewire/React, not what those libraries do in general.
- **Unstable detail stays out.** Exact selector chains, payload shapes and
  ephemeral ids are re-derivable from source and go stale silently.
- **One home per fact.** A new front end gets a file; a new business area gets a
  domain file. Neither may restate what `architecture.md` already says.

## Files

| File | Owns |
| --- | --- |
| `README.md` | Entry point: what this context is, how to navigate it, what to read per task type. Routes only. |
| `config.md` | Update mode, detail level, scope. Read before writing. **Also** the environment variables, their defaults, and why there is no default user. |
| `structure.md` | This contract. |
| `architecture.md` | Layering, the entry points, the per-user client model, threading model, where state lives. |
| `conventions.md` | Patterns a new file must follow, and where the current code knowingly departs from them. |
| `database.md` | Engine setup, entity relationships, the rebuild-not-migrate policy, how sessions are persisted. |
| `api.md` | The HTTP surface's shape and rules: the two credential systems, the CLI-mirroring rule, response contracts. |
| `workflows.md` | Multi-step flows that cross layers: session bootstrap, cart mutation, checkout, order lifecycle. Points at domains for the rules. |
| `dashboard.md` | The admin dashboard: the Vite project in `public/`, the build, how it is served, and the conventions its code follows. |
| `tracking.md` | Product change tracking and the cron queue: subscriptions, deduplication, the change log, scheduling and locking. |
| `domains/README.md` | Index of the domains and when to read each. |
| `domains/authentication.md` | API keys, dashboard passwords and tokens, roles, per-user sawa9ly sessions. |
| `domains/orders.md` | Order lifecycle, state machine, the internal-vs-sawa9ly product id boundary. |
| `domains/checkout.md` | Driving the site's two-step checkout; the commission floor; dry-run semantics. |
| `domains/catalogue.md` | Saved product info and delivery clients as reference data. |

### What does not belong anywhere here

- Anything already stated as a rule in `AGENTS.md` (classes everywhere,
  indentation, error wording, the `foreign_keys` pragma, never committing
  secrets). Restate only the *consequence* a reader cannot get from the rule.
- Column-by-column table definitions → `src/models/`.
- Route-by-route or command-by-command listings → `src/controllers/`, `cli/`.
- Selector strings, Livewire payload internals, `wire:id` ids.
- Session cookies, API keys, credentials, ids from a past test run.

## Creating Files

Create a file only when its subject becomes real, and fold it into an existing
file when it would merely duplicate one.

- `decisions.md` — create when a choice is made that a later reader could
  reasonably reverse (e.g. storing API keys hashed, DB-backed sessions replacing
  a session file). Only the decision, its reason, and what it cost.
- `infrastructure.md` — create on first deployment story (Docker, systemd,
  reverse proxy, CI). Until then this project's deployment is "run uvicorn".
- `domains/<new>.md` — create when a business area gains its own rules, entities
  and workflow. A second payment method, a returns flow, a shipping integration.
  Not for a new table or a new endpoint.

## Per-Level Structure

- **minimal** — `README.md`, `config.md`, `structure.md`, `architecture.md`.
  Enough to know what the project is and where things live.
- **standard** — minimal plus `conventions.md`, `database.md`, `api.md`,
  `workflows.md`, `dashboard.md`, `tracking.md`, `domains/`. *This is the current
  level: exactly these files exist, no more.*
- **detailed** — standard plus `decisions.md`, `infrastructure.md`, and deeper
  per-domain files only where a domain genuinely has more to say.

## Domain Organisation

`domains/` holds business areas, not technical layers. A domain file carries:
purpose, the entities involved, the rules that constrain it, the workflow, and
the constraints that are not obvious from reading the code.

The test for a domain file: it exists because the rules in it would be violated
by a plausible-looking change. `orders.md` earns its place — nothing in the
code stops you from skipping the state machine or sending an internal product id
to the site.
