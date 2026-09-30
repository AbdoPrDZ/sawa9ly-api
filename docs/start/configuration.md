# Configuration

Every environment variable the project reads is declared in one place,
`src/config.py`. Nothing else in the codebase touches the environment, so that
file is the whole answer to "what can I configure?".

**Required**

| Variable | Meaning |
| --- | --- |
| `SUPER_ADMIN_USERNAME` | Username of the root dashboard account |
| `SUPER_ADMIN_PASSWORD` | Its password |

Both are required on a database with no `super` user: the app creates the
account from them at startup, and **refuses to start** without them. There is no
default for either. Once a super exists both are ignored, so changing them does
not reset the password.

**Database** — leave all unset for SQLite in `database/sawa9ly.db`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | — | A full SQLAlchemy URL; wins over everything below |
| `SQLITE_FILE` | `database/sawa9ly.db` | Where the SQLite file lives |
| `DB_DRIVER` | `postgresql` | `postgresql` or `mysql`, used when `DB_NAME` is set |
| `DB_HOST` | `localhost` | |
| `DB_PORT` | per driver | 5432 for postgres, 3306 for mysql |
| `DB_NAME` | — | Setting this is what switches off SQLite |
| `DB_USER` / `DB_PASSWORD` | — | URL-encoded automatically |

**HTTP server**

| Variable | Default | Meaning |
| --- | --- | --- |
| `API_HOST` | `127.0.0.1` | |
| `API_PORT` | `8000` | |
| `API_RELOAD` | `false` | `true`/`1`/`yes`/`on` to enable |

Each of the three can be overridden per run: `main.py serve --port 9000`.

**Where things are written** — three directories beside the source, kept apart
because they are wanted on different terms.

| Directory | Holds | Back it up? |
| --- | --- | --- |
| `database/` | `sawa9ly.db`, the SQLite file | Yes. It is the accounts, API keys and order history |
| `data/` | working state: `cron.lock` and `telegram.lock` | No |
| `logs/` | the five log files below | No. Large and disposable |

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_DIR` | `database` | Where `sawa9ly.db` is created |
| `DATA_DIR` | `data` | Where the lock files are created |
| `LOG_DIR` | `logs` | Where the log files are created |
| `LOCK_DIR` | `DATA_DIR` | Where the lock files go, if not with the rest of `DATA_DIR` |

A relative value is resolved against the project root, so `database` and
`./database` mean the same thing however the command was invoked.

Plain `python src/server.py` does not work — it cannot import `src` from inside
the package. Use `python main.py serve`, or `python -m src.server`.

**Dashboard**

| Variable | Default | Meaning |
| --- | --- | --- |
| `DASHBOARD_SECRET` | generated once, stored in the db | Signing key for session tokens |

**Tracking queue**

| Variable | Default | Meaning |
| --- | --- | --- |
| `CRON_INTERVAL` | `300` | Seconds between passes |
| `CRON_DELAY` | `1.0` | Seconds between products inside one pass |

**Telegram**

| Variable | Default | Meaning |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather. Unset means the integration is off |
| `TELEGRAM_BOT_NAME` | from the token | Fallback bot @username, if Telegram cannot be asked |

Set it explicitly on a server so tokens survive a database restore.
