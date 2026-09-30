# Database

SQLAlchemy 2.x with `DeclarativeBase` and `Mapped[]` annotations. SQLite by
default, overridable with `DATABASE_URL` for a server deployment.

## Setup facts that matter

- The default file is `database/sawa9ly.db`, created relative to the project root, not
  the working directory. `database/` is gitignored because it holds live session
  cookies and per-user passwords.
- **`PRAGMA foreign_keys=ON` is set per connection by an engine event.** Without
  it every `ON DELETE CASCADE` in the schema silently does nothing, so deleting a
  user orphans their settings, keys, clients and orders. Any new connection path
  must go through the same engine.
- **Every process calls `ensure_db()` before it touches an entity**, and "every
  process" is not a figure of speech: under Docker the API, the queue and the bot
  are three containers starting at once against one database. The API does it when
  `create_app` builds the app, the CLI when it opens a `Cli.db()` session, and the
  two long-running listeners do it themselves in their CLI `dispatch`/`_listen` —
  because they open their own sessions and never pass through `Cli.db()`. That gap
  was a real race: the queue asked for `trackers` and `orders` half a second
  before the API's `create_all` had made them, and reported a missing relation
  rather than the thing that was true. A new long-running entry point needs the
  same call, or `depends_on` is doing a job it cannot do.
- `check_same_thread=False` is required for SQLite because FastAPI's threadpool
  hands a session to a worker thread.
- `init_db()` calls `create_all`, which **creates missing tables and nothing
  else**. It does not alter, migrate or backfill an existing file. The project is
  **not in production, so a schema change means editing the model and deleting
  `database/sawa9ly.db`** to rebuild it. There is deliberately no migration runner.
  Stop any running server first — an open connection keeps the file locked on
  Windows and the delete fails.
- `session_scope()` is a session usable as a context manager. Controllers get one
  via `Dependencies.get_db`; CLI commands open one per command. There is no unit
  of work and no nested-transaction machinery, so keep each command or request
  inside a single session.

## Entities and how they relate

`User` is the aggregate root. Everything except `Product` hangs off it.

- **`User`** — the account we act as. Holds `username`, the sawa9ly `email` and
  `password` for logging into the site, a `role` (`super`, `admin` or `user`), and
  an optional `password_hash` for the dashboard. It owns settings, API keys,
  clients, orders and trackers; deleting a user cascades to all of them.
- **`Secret`** — app-wide, not per user. Holds generated secrets, currently only
  the dashboard token signing key, so a restart does not invalidate every
  session. `__repr__` deliberately omits the value: a repr in a log or a
  traceback would leak it.
- **`Tracker`** — a user's subscription to a watched entity: `target_model` names
  the entity and `target_id` is that entity's own primary key, so deleting a
  product cascades its subscriptions away. Unique per `(target, user)` rather
  than per target, which is what lets several users watch one product. See
  `tracking.md`.
- **`Setting`** — per-user key/value. This is where the session cookie lives
  (`SESSION_KEY`). The uniqueness that matters is per user *and* key.
- **`ApiKey`** — belongs to a user, stores only a SHA-256 `key_hash` plus a short
  `prefix` for display. There is a single global uniqueness on the hash, so
  lookup by plaintext is `ApiKey.find`, and a revoked or expired key is still a
  row — validity is a check, not a deletion.
- **`Product`** — the catalogue. Global, not per user: `product_id` holds the
  sawa9ly id and is unique. Images, figures and categories are stored as JSON
  text, because they are opaque lists of strings from the site and nothing
  queries inside them.
- **`Client`** — a delivery recipient, per user. Referenced by orders, and its
  fields are what the checkout form is filled from.
- **`Order`** — belongs to a user, optionally to a client. Deleting a client sets
  its orders' `client_id` to null rather than deleting them; an order must not
  vanish because a recipient was removed from the address book.
- **`OrderLine`** — belongs to an order and to a catalogue `Product`. `quantity`
  and `price` live here, and the subtotal is derived, not stored.

The `products` table is referenced by `order_lines`, so catalogue rows are a
shared dependency: deleting a saved product cascades to the order lines pointing
at it. That is a real hazard for an order history and is worth reconsidering
before adding a delete command.

## The two product ids

This trips up almost every change that touches orders.

`Product.id` is our autoincrement primary key. `Product.product_id` is the
sawa9ly id the site and the CLI speak. `OrderLine.product_id` is a foreign key to
the **internal** `products.id`, despite the name.

So an order line needs translation in both directions, and the site must never
receive an internal id. `OrderService` owns that translation; see
`domains/orders.md`.

## Timestamps

`utcnow()` is the column default and is timezone-aware. Read them back as
timezone-aware; do not compare against a naive `datetime.now()`.

## Conventions for queries

Go through entity classmethods. There is no ad-hoc SQL in the project and no
query string is ever built from user input — an id from a URL or a command line
arrives as `int` because the parser and the path converter both coerce it.
