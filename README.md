# Sawa9ly API

A client for [sawa9ly.app](https://sawa9ly.app) — a Livewire/Laravel storefront —
covering product scraping, delivery prices, cart management, and order checkout.

The site is driven by Livewire v3, so nothing here is plain HTTP. Every action is
a `POST` to `/livewire/update` carrying the component's `wire:snapshot`;
`src/utils/livewire.py` speaks that protocol and the models on top of it read like
ordinary objects.

It comes as three things over the same code: a **command line** client, an **HTTP
API** for your own programs, and an **admin dashboard** for the people who run it.

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
database:

```bash
sqlite3 database/sawa9ly.db < src/seeds/wilayas_communes.sql
```

The delivery prices and the recipient form both need them, and without them the
first `shipping sync` stops and tells you to run exactly that. On Docker the
`sqlite` service has the file mounted, so the same one-liner works inside it.

Or, in containers:

```bash
cp .env.docker.example .env.docker
docker compose --env-file .env.docker -f docker-compose.sqlite.yml up -d --build
```

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
