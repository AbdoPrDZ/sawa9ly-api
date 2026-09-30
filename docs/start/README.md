# Getting started

## Requirements

- Python 3.10+ (developed on 3.14)
- `requests`, `python-dotenv`, `pyquery` (see `requirements.txt`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

Then decide who the root dashboard account is, and put it in `.env`:

```dotenv
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=a-long-password
```

Those two are the only settings you have to make. On startup the app creates
that user with the `super` role if no super account exists yet, and **refuses to
start** if there is no super and these are not set — there would be no way to
sign in. Once a super exists the variables are ignored, so changing them does
*not* reset the password; use `python main.py user set-login-password` for that.

The site's own credentials are not in `.env`. They belong to a user, recorded
once:

```bash
python main.py user add alice --email you@example.com --password ...
```

Everything else is optional and documented in
[Configuration](configuration.md) — database, port, logging. Calling the HTTP API
is covered in [the HTTP API guide](../guides/http-api.md).

## Installing the package (optional)

The venv route above runs from a checkout, which is the normal way to use this.
You can also install the package, which gives you a `sawa9ly` command and lets
you run `python -m sawa9ly <command>` from any directory.

There are two ways to install. Neither needs `setuptools` or `wheel` — pip
supplies the build backend itself, in a throwaway environment that is discarded
afterwards, so neither ends up in your runtime.

**From a clone** — the normal choice if you want to read or edit the code:

```bash
git clone https://github.com/AbdoPrDZ/sawa9ly-api.git
cd sawa9ly-api
python -m venv .venv
.venv\Scripts\activate              # Windows
.venv/bin/activate                  # macOS / Linux
pip install .
```

**Straight from the repository**, without cloning it first:

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
.venv/bin/activate                  # macOS / Linux
pip install git+https://github.com/AbdoPrDZ/sawa9ly-api.git
```

Either way you then get all three forms, which are the same parser — so every
command in this README works with any of them:

```bash
sawa9ly user list
python -m sawa9ly user list
python main.py user list             # from inside a clone
```

To upgrade a git install later, add `--upgrade`. To pull a fix without
reinstalling, use `pip install --force-reinstall` — a plain reinstall is
caching:

```bash
pip install --upgrade --force-reinstall git+https://github.com/AbdoPrDZ/sawa9ly-api.git
```

**Know this before you rely on an install.** An installed copy resolves its paths
from its own location inside `site-packages`, not from your project directory,
so:

- the database is created at `site-packages/database/sawa9ly.db` — a **separate,
  empty** database, not the one your checkout uses;
- the dashboard is not served, because `dashboard/dist` is not part of the
  distribution, so `/` returns 404 while the API routes still work;
- `serve` needs `SUPER_ADMIN_USERNAME` and `SUPER_ADMIN_PASSWORD` set, or an
  existing super in that separate database, or it refuses to start.

Read-only commands against the live site work fine. Anything that should see
your real users, keys, orders or cart wants a clone and `python main.py`.
Pointing an install at a different directory is `DATABASE_DIR`, `DATA_DIR` or
`LOG_DIR` in `.env`; see [Configuration](configuration.md).

## The default user is the super admin

`--user` is optional. A command that acts for an account and was not told which
one falls back to the `super`:

```bash
python main.py cart show                    # acts as the super
python main.py cart show --user alice       # acts as alice
python main.py order list
```

The super is read from the **database**, not from the environment, so nothing in
`.env` can quietly point a command at an account nobody named. It is found by
`Cli.super_username()` in `cli/base.py`:

- one super → that one is used;
- several, and `SUPER_ADMIN_USERNAME` names one of them → that one is used;
- several, and it names none of them → the CLI lists them and exits, rather than
  picking one at random. Pass `--user` to be explicit;
- none at all → it says how to create one.

Commands that need no account — `user list`, `catalogue show`, `serve` — do not
take one.

`--user` is resolved once in `App.run` before dispatch, so no command group knows
the fallback exists and every one of them receives a concrete account name.

## How the session is kept

Login state lives in the database (`database/sawa9ly.db`), in the `settings` table
of the user it belongs to:

1. **First run** — the user has no session, so the app posts to `/login` with
   that user's stored credentials and keeps the cookie against their row.
2. **Later runs** — the stored session is loaded and reused, no login request.
3. **When the stored session stops working** — Laravel sessions expire, and a
   stale one is detected by checking whether an authenticated page still loads.
   The app logs in again and overwrites the row. A session that expires
   *during* a run is also refreshed automatically and the request retried.

So an expired session never needs manual attention, and credentials are only
used when a login is actually required.

Every user has its **own** credentials and its **own** session, so two users
never share a cart and neither can borrow the other's account. A user with no
credentials recorded simply cannot sign in, and the error says which command
records them.

An account is required — a guest hitting a product or cart URL is redirected to
`/login`.

> `.env` and `database/` are both secrets and both gitignored. See
> [Security](../reference/security.md) for how to handle them.

> Stored cookies are bound to the `sawa9ly.app` apex domain on purpose. The
> site also answers on `sawa9ly.com`, and domain-less cookies get duplicated in
> the jar, which makes Laravel read a stale session.
