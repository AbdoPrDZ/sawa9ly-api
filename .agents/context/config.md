# Configuration

Two unrelated things are configured in this project, and this file holds both:
how the *context* is maintained, and what the *application* reads from the
environment.

---

# Context Configuration

Update Mode: automatic

Detail Level: standard

Scope: project + domains

Template: none (generic — no bundled template matches this stack)

## What these values mean

- **Automatic** — after a Level 2–3 change (see `structure.md`), update only the
  affected context files, verify them against the source, and continue without
  asking. Report what was updated.
- **Standard** — capture architecture, conventions, data model, API surface,
  workflows, integrations and key decisions. Skip per-class, per-column and
  per-endpoint inventories.
- **Project + domains** — project-wide files plus one per meaningful business
  domain under `domains/`.

---

# Environment Configuration

Every environment variable the project reads is declared in `src/config.py`, as
one `Config` class. No other module calls `os.getenv`. Read that file for the
authoritative list; the table here is a summary, not a copy.

## Why one file

Configuration is scattered by nature: a database URL in one module, a port in
another, a credential in a third. Gathering it means one place to read, one
place to add a variable, and no module that quietly depends on the environment
on its own. Values are read through methods rather than at import time, so a
test can change the environment and re-read.

## What is configurable

| Group | Variables | Default |
| --- | --- | --- |
| Database | `DATABASE_URL`, or `SQLITE_FILE`; or `DB_DRIVER`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | SQLite at `data/sawa9ly.db` |
| HTTP server | `API_HOST`, `API_PORT`, `API_RELOAD` | `127.0.0.1:8000`, reload off |
| Logging | `LOG_LEVEL`, `LOG_FILE`, `LOG_FORMAT` | `WARNING`, console, text |
| Super admin | `SUPER_ADMIN_USERNAME`, `SUPER_ADMIN_PASSWORD` | none — both required |
| Dashboard | `DASHBOARD_SECRET` | generated once, stored in the database |

`DATABASE_URL` wins over the discrete `DB_*` variables. Credentials are
URL-encoded when a URL is assembled from parts, because a password containing
`@` or `/` would otherwise parse into the wrong place.

## The default user is the super admin

`--user` is **optional**. A command that acts for an account and was not told
which one falls back to the `super`, resolved from the database by
`Cli.super_username()` — not from the environment, so nothing in `.env` can
quietly redirect a command onto an account nobody named.

There is still no `DEFAULT_USER` setting and no `Livewire()` with no arguments:
every page service requires a client. What changed is only that the CLI may
supply the name for you.

**An installation with more than one `super` is refused, not guessed at.** If
`SUPER_ADMIN_USERNAME` names one of them that one is used; otherwise the CLI
lists the candidates and exits rather than picking the earliest-created, which
would be the silent-wrong-account problem the original rule existed to prevent.
The same reasoning removed the `SAWA9LY_EMAIL` / `SAWA9LY_PASSWORD` fallback:
every user stores its own site credentials, so an API-key user can never silently
borrow the operator's account.

The resolution happens once in `App.run`, before dispatch, so every command group
receives a concrete name and none of them knows the fallback exists.

## Booleans are parsed, not coerced

`bool(os.getenv(...))` is wrong — it makes the string `"false"` true. `Config`
recognises `1/true/yes/on` and treats everything else as false.

## Logging is off until asked for

The default level is `WARNING` and nothing goes to a file, so a normal run is
quiet. `LOG_LEVEL=INFO` or `LOG_FILE` turns it up. `src/logging_setup.py` holds
the handlers and a filter that redacts any log line mentioning a password,
token, key or cookie — the project handles all four, and a stray
`logger.info("%s", user)` would otherwise put a credential in a log file.

The filter is idempotent because a record is passed to every handler, and both a
console and a file handler are configured.

It matches on the **message text**, not on the argument values, and `SECRET_WORDS`
contains `credential`, `token` and `cookie`. So a message like "the site rejected
the credentials" loses its arguments and prints a literal `%s` followed by
`[redacted]`. Write log messages around those words — "the site refused the
sign-in" — or the line silently stops carrying the username it was written to
carry.

### Where the configuration is actually applied

`configure_logging()` has exactly one call site: the `__main__` block of
`src/server.py`. The two documented run paths — `python main.py serve`
(`ServeCli.dispatch` calls `uvicorn.run` itself) and `uvicorn src.server:app` —
never reach that block, so on a normal run the `LOG_*` variables are read but
never applied, and no log file is created.

A quiet run is therefore not evidence of a bad `.env`. Two independent reasons
apply, and both are true at once:

- **Nothing emits from most modules.** The log lines that exist are in
  `src/utils/livewire.py` (session lifecycle and transport) and
  `src/services/cart.py` (checkout stages); nothing in `cli/`, `src/services/`
  beyond the cart, `src/controllers/` or `src/models/` logs at all. Adding the
  first call in a new module is what makes `LOG_LEVEL` observable there.
- **Uvicorn logs itself.** It applies its own `dictConfig` to the `uvicorn`,
  `uvicorn.error` and `uvicorn.access` loggers with its own handlers, without
  touching the root logger. That is why startup and access lines appear at all
  when `configure_logging()` has not run.

So a fix has two halves, and doing only the first changes nothing visible: call
`configure_logging()` on the path that actually starts the server, and emit
records from the code that needs diagnosing.
