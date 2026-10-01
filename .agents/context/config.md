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
| Database | `DATABASE_URL`, or `SQLITE_FILE`; or `DB_DRIVER`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | SQLite at `database/sawa9ly.db` |
| HTTP server | `API_HOST`, `API_PORT`, `API_RELOAD` | `127.0.0.1:8000`, reload off |
| MCP server | `MCP_HOST`, `MCP_PORT`, `MCP_PATH`, `MCP_PUBLIC_URL` | `127.0.0.1:8001`, `/mcp/`, no public URL |
| Locations | `DATABASE_DIR`, `DATA_DIR`, `LOG_DIR`, `LOCK_DIR` | `database`, `data`, `logs`, and `DATA_DIR` for the locks |
| Logging | `LOG_LEVEL`, `LOG_FILE`, `LOG_FORMAT` | `INFO`, five files, text |
| Super admin | `SUPER_ADMIN_USERNAME`, `SUPER_ADMIN_PASSWORD` | none — both required |
| Dashboard | `DASHBOARD_SECRET` | generated once, stored in the database |
| Tracking queue | `CRON_INTERVAL`, `CRON_DELAY` | 300s, 1.0s |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_NAME` | none — the integration is off when unset |

`DATABASE_URL` wins over the discrete `DB_*` variables. Credentials are
URL-encoded when a URL is assembled from parts, because a password containing
`@` or `/` would otherwise parse into the wrong place.

`TELEGRAM_BOT_TOKEN` is a **credential** and the one most likely to leak: the Bot
API puts it in the URL of every call, so `requests` quotes it in error messages.
`TELEGRAM_BOT_NAME` is a fallback only — the bot's real name is read from the token
with `getMe`, so a link cannot name a bot the token does not belong to. See
`domains/telegram.md`.

## The MCP server's own settings

`MCP_HOST`/`MCP_PORT`/`MCP_PATH` are the API's three with different names, and the
naming is the point: they are a different server on a different port with a
different credential, so they do not fall back to `API_*`. A deployment that set
`API_HOST=0.0.0.0` for a reverse proxy has **not** exposed the MCP server, and
that is the desired outcome — the MCP surface can place orders.

`MCP_PUBLIC_URL` is a **third** address, and the easiest one to get wrong,
because it is not either of the other two:

| | the question it answers |
| --- | --- |
| `MCP_HOST` | what the process binds *inside* the container — `0.0.0.0` under Docker, or the port mapping goes nowhere |
| `MCP_PUBLISHED_HOST` | what Docker exposes on the machine — `127.0.0.1` by default |
| `MCP_PUBLIC_URL` | what a *client* connects to, which is what the sign-in redirect sends a browser to |

It must be `https`: Claude and every other remote MCP connector refuse plain
HTTP, so an unset or `http://` value fails at the connector rather than in this
container. `main.py mcp` prints the URL to paste and says which of these is wrong.

`MCP_PATH`'s trailing slash is load-bearing. The streamable-HTTP transport is
mounted as a prefix, and a client pointed at `/mcp` without the slash gets a
redirect rather than a session.

## The MCP server's own settings

`MCP_HOST` defaults to loopback rather than to `API_HOST`, because an MCP client
is normally another process on the same machine. Setting it to `0.0.0.0` is
allowed and is not warned about — it is a legitimate container deployment — but
with sign-in in place what loopback protects is smaller than it looks: the
endpoint itself demands a credential, and what is still open to anyone who can
reach the port is the pair of discovery documents under `/.well-known/`. See
`mcp.md`.

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

## Three directories, and why they are three

The application writes to three places, deliberately separate, because they are
wanted on different terms — backing up one should not mean keeping the others.

| Directory | Holds | Set by |
| --- | --- | --- |
| `database/` | `sawa9ly.db` | `DATABASE_DIR` |
| `data/` | the lock files | `DATA_DIR` |
| `logs/` | the five log files | `LOG_DIR` |

`LOCK_DIR` has no default of its own and falls back to `DATA_DIR`, so a
deployment that sets only `DATA_DIR` stays self-consistent.

`Config.data_dir()`, `database_dir()`, `lock_dir()` and `log_dir()` are
**classmethods, not class attributes**, and all four go through `Config._resolve`,
which leaves an absolute path alone and resolves a relative one against
`PROJECT_ROOT`. Two reasons, both load-bearing:

- Reading the environment at import time freezes the value before anything can
  set it, which is what made the locations unconfigurable in the first place.
- A class body cannot call a classmethod: at that point it is still a
  `classmethod` object rather than a bound method, so `DATA_DIR = data_dir()`
  raises `TypeError: 'classmethod' object is not callable`. There is no way to
  have both, and the method is the one that works.

**Under Docker the image relocates all three** and sets them as environment
variables rather than compiling them in, so the same image run on a machine puts
them back beside the source: database `/var/lib/sawa9ly`, logs `/var/log/sawa9ly`,
locks `/tmp/sawa9ly`.

**Four containers from one image:** `serve`, `telegram`, `cron`, `mcp` — the same
command-to-service pattern as the first three, so the MCP server ships with the
stack rather than being something a deployment has to remember to add. `mcp` is
the only one of the four that can be left off entirely.

The two published addresses are `API_PUBLISHED_HOST` and `MCP_PUBLISHED_HOST`,
both defaulting to `127.0.0.1`. They are separate from `API_HOST`/`MCP_HOST`
because the two answer different questions: the `*_HOST` pair is what the process
binds *inside* the container, where the loopback interface is the container's own
so it must be `0.0.0.0`, and the `*_PUBLISHED_HOST` pair is what Docker exposes on
the machine. `*_PUBLISHED_PORT` sits beside the host pair and `*_PORT` beside the
container pair, for the same reason.

The locks move to `/tmp` on purpose. A lock file only means anything while the
process holding it is alive, and `Cron._Lock` is an `O_EXCL` create rather than a
flock, so one left by a killed process is a stale file to be reported rather than
a lock to wait on. A container's writable layer is discarded with the container,
so a lock has nothing worth surviving it, and giving it a volume would be the
opposite of what a volume is for.

## Logging is on by default, and split by subsystem

`src/logging_setup.py` owns it. The level defaults to `INFO` and the files are on,
because the queue and the bot are run in the background and then never seen again
— their pass summaries are the only record that they ran at all.

One file per subsystem, because the api, the dashboard, the CLI, the queue and the
bot fail separately. `LOG_DIR` (default `logs/`, resolved against the project
root like every default here) holds them:

| File | Routed by logger name |
|---|---|
| `sawa9ly-api.log` | `src.server`, `src.controllers`, `src.services` (not the cron ones), `src.utils`, `src.db`, `uvicorn*` |
| `sawa9ly-dashboard.log` | `src.controllers.dashboard_log` only |
| `sawa9ly-cli.log` | `cli.*` |
| `sawa9ly-cron.log` | `src.services.{cron,tracking,order_sync,notifications}` |
| `sawa9ly-telegram.log` | `src.utils.telegram`, `src.services.telegram` |

`LOG_FILE` replaces all five with one file, for whoever wants a single stream.

**Routing is by logger name, not by process.** `serve` is one process serving both
the API and the dashboard, and every CLI command is a separate process that can
touch any subsystem, so a process-based split would not hold. `SUBSYSTEMS` in
`logging_setup` is an ordered tuple of prefixes and a record belongs to the **first**
match, on a dot boundary — so `src.services.telegram` must be listed before
`src.services`, and an unrelated `src.services.telegramish` is not swallowed by it.
Anything unrecognised goes to the api, the widest thing here, rather than vanishing.

A file is created on its first write (`delay=True`), and its directory at the same
moment (`SubsystemFileHandler._open`). An install that has logged nothing has no
empty files and no empty `logs/` directory.

### The dashboard log is written by hand, not filtered out of uvicorn's

`src/controllers/dashboard_log.py` is raw-ASGI middleware that logs only
`/dashboard*` and `/pages*`. The obvious alternative — splitting uvicorn's access
log by path — depends on the shape of uvicorn's access-log arguments, which is an
internal detail. `/api` calls made by the dashboard are the api log's business.

It is written as raw ASGI rather than `BaseHTTPMiddleware` because a middleware
that only observes a request has no business buffering the response, and this app
serves the dashboard bundle.

### The access log is pinned to INFO

`ALWAYS_INFO_LOGGERS` holds `uvicorn`, `uvicorn.access` and `uvicorn.error` at INFO
whatever `LOG_LEVEL` says. An api log that has stopped recording who called what is
not an api log, and raising the level to quiet an application's own debugging
should not delete the traffic history with it. Nothing is lost: a higher level only
means fewer of the project's *own* lines.

### Secrets are redacted out of the finished line

`SecretFilter` strips the value after any `password`/`token`/`cookie`/`secret`/
`api_key`/`authorization`/`credential` field, in the **rendered** message. This
matters: the previous version only cleared `record.args`, which helped a caller who
passed the secret as an argument (`logger.info("login %s", pw)`) and did nothing at
all for one who built the string first (`logger.info(f"login {pw}")`), and it
dropped the arguments of *un*redacted records too, so those lines were written out
as a literal `%s`. Redacting after `getMessage()` covers both caller styles.

It cannot see a Telegram token in a URL — `/bot<TOKEN>/sendMessage` has no field
name before it — so `Telegram._redact` remains the thing that handles that, and is
not redundant. Keep both.

A filter runs once per handler and there are six of them, so the result is marked on
the record (`_sawa9ly_redacted`) and computed once; otherwise one secret would be
marked six times or a record could reach one handler unredacted and the next
redacted.

### Talking to a container

`bin/sawa9ly-api` is installed at `/usr/local/bin/sawa9ly-api` in the image, so
`docker exec <container> sawa9ly-api <args>` reaches the CLI without a shell. It is
`exec python -m sawa9ly "$@"` and nothing else, deliberately:

- `exec`, so the exit status is the CLI's own. `cron run` signals a failed pass
  through it, and a wrapper that swallowed that would report a broken queue as a
  healthy one.
- `-m sawa9ly` rather than `python /app/main.py`, so the working directory does not
  matter — `docker exec -w` can change it, and a command that only works from one
  directory fails in a way that looks like a bug in the command. The image sets
  `PYTHONPATH=/app` to make this true from anywhere.
- No argument handling of its own, because anything it accepted and ignored would
  be a command that appeared to work and did nothing.

The Dockerfile `chmod 755`s it rather than trusting the file's own mode: a
checkout on Windows has no executable bit for `COPY` to preserve, and the script
would arrive as a 0644 file the container cannot run.

### Where the configuration is actually applied

`configure_logging()` is called from `App.main()`, so every command is covered, and
again in `ServeCli.dispatch` and in the `__main__` block of `src/server.py`. Both
`uvicorn.run` calls pass `log_config=UVICORN_LOG_CONFIG` (None), because uvicorn
otherwise installs its own `dictConfig` over the root logger and every file stays
empty.

Both doors onto the server work: `python main.py serve` and `python -m src.server`.
Plain `python src/server.py` does **not** — running a file inside the package puts
`src/` on `sys.path` rather than the root, so `import src.config` fails. It never
worked; the old `.env.example` claimed otherwise.

### What emits

Emitting is still sparse outside the queue, the bot and the CLI, and that is the
remaining half of the problem if a subsystem's file is empty: nothing in
`src/services/` beyond the cron-related ones, and nothing in `src/models/`, logs at
all. Adding the first call in a module is what makes it appear. `Cron._say` writes
to stderr *and* the cron log, because stderr alone is not a record once the process
is backgrounded.
