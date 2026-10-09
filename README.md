# Sawa9ly API

A client for [sawa9ly.app](https://sawa9ly.app) — a Livewire/Laravel storefront —
covering product scraping, delivery prices, cart management, and order checkout.

The site is driven by Livewire v3, so nothing here is plain HTTP. Every action is
a `POST` to `/livewire/update` carrying the component's `wire:snapshot`;
`src/utils/livewire.py` speaks that protocol and the models on top of it read like
ordinary objects.

It comes as four things over the same code: a **command line** client, an **HTTP
API** for your own programs, an **admin dashboard** for the people who run it, and
a **public storefront** each user can sell from.

## Requirements

- Python 3.10+ (developed on 3.14)
- `requests`, `python-dotenv`, `pyquery` (see `requirements.txt`)

## Quickstart

```bash
git clone https://github.com/AbdoPrDZ/sawa9ly-api.git
cd sawa9ly-api
python -m venv .venv
.venv\Scripts\activate                  # Windows
.venv/bin/activate                      # Linux / macOS
pip install -r requirements.txt
```

Then decide who the root dashboard account is, and put it in `.env`:

```dotenv
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=a-long-password
```

Those two are the only settings you have to make. On startup the app creates that
user with the `super` role if no super account exists yet, and **refuses to
start** if there is no super and these are not set — there would be no way to sign
in. Once a super exists they are ignored, so changing them does *not* reset the
password; use `python main.py user set-login-password` for that.

The site's own credentials are not in `.env`. They belong to a user, recorded once:

```bash
python main.py user add alice --email you@example.com --password ...
```

Now start the server, which also serves the dashboard:

```bash
python main.py serve
```

- Dashboard: <http://127.0.0.1:8000/dashboard/>
- API reference: <http://127.0.0.1:8000/docs>

### One thing to load first

The 58 wilayas and their 1541 communes are reference data the site publishes
rather than something this client scrapes, so they are seeded once into an empty
database. Both delivery prices and the recipient form need them, and without them
the first `sync` stops and tells you to run this.

**From the application, whichever database you point it at:**

```bash
python main.py shipping seed
```

That is the one to use inside a container. It goes through the application's own
engine and the configured `DATABASE_URL`, so it needs no database client at all —
which matters because the application image ships `psycopg` and no `psql`, so on a
VPS there is nothing else to run it with.

The file is plain SQL, so a client works too, if you have one:

```bash
sqlite3 database/sawa9ly.db < src/seeds/wilayas_communes.sql
psql "$DATABASE_URL" -f src/seeds/wilayas_communes.sql
```

Re-running is safe but clears the saved delivery prices, since they point at the
wilayas; one `python main.py shipping sync` restores them.

Or, in containers:

```bash
cp .env.docker.example .env.docker
docker compose --env-file .env.docker -f docker-compose.sqlite.yml up -d --build
```

### Upgrading an existing database

`create_all` creates missing tables and never columns, so a deployment whose
database predates a column change has to be brought forward with the schema
steps. That command is idempotent and uses the application's own connection — the
image ships no `psql`:

```bash
# In a container, before the new code serves traffic:
docker compose --env-file .env.docker -f docker-compose.postgres.yml \
  run --rm serve sawa9ly-api db migrate

# Or directly, in the app's environment:
python main.py db migrate
```

**Back the database up first.** The list of steps — and there is deliberately no
migration framework — is in `src/services/migrations.py`.

## Documentation

The rest is in **[`docs/`](docs/README.md)**, split so each file answers one
question:

| | |
| --- | --- |
| [`start/`](docs/start/README.md) | Getting it running — install, first run, configuration, Docker |
| [`guides/`](docs/guides/cli.md) | Doing a thing — the CLI, the HTTP API, the dashboard, pages, tracking, Telegram |
| [`reference/`](docs/reference/routes.md) | Looking something up — the route table, logging, project layout, caveats, security |

The three common starting points:

- **Running it somewhere** — [install and first run](docs/start/README.md), then
  [configuration](docs/start/configuration.md) or [Docker](docs/start/docker.md).
- **Driving it** — [the command line](docs/guides/cli.md) or
  [calling the HTTP API](docs/guides/http-api.md).
- **Working on it** — [project layout](docs/reference/project-layout.md),
  [logging](docs/reference/logging.md), and
  [how the site really behaves](docs/reference/site-behaviour.md) before changing
  anything that scrapes.

Two things worth knowing before you rely on either:

- **An order placed through this client cannot be cancelled from here.** There is
  no undo endpoint, because there is no undo at the site. Use `--dry-run`, or
  submit with a client field missing so the site rejects it.
- **The queue and the bot are separate processes** from the API, each with its own
  lock and its own log. See [tracking](docs/guides/tracking.md) and
  [Telegram](docs/guides/telegram.md).

## Working on this

`AGENTS.md` holds the rules for changing the codebase, and `.agents/context/` a
compressed description of it for an agent starting cold.
