# Sawa9ly API

A client for [sawa9ly.app](https://sawa9ly.app) — a Livewire/Laravel storefront —
covering product scraping, cart management, and order checkout.

The site is driven by Livewire v3, so nothing here is plain HTTP. Every action
is a `POST` to `/livewire/update` carrying the component's `wire:snapshot`;
`src/utils/livewire.py` speaks that protocol and the models on top of it read
like ordinary objects.

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
[Configuration](#configuration) — database, port, logging. Calling the HTTP API
is covered in [API_GUIDE.md](API_GUIDE.md).

### Installing the package (optional)

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

- the database is created at `site-packages/data/sawa9ly.db` — a **separate,
  empty** database, not the one your checkout uses;
- the dashboard is not served, because `public/dist` is not part of the
  distribution, so `/` returns 404 while the API routes still work;
- `serve` needs `SUPER_ADMIN_USERNAME` and `SUPER_ADMIN_PASSWORD` set, or an
  existing super in that separate database, or it refuses to start.

Read-only commands against the live site work fine. Anything that should see
your real users, keys, orders or cart wants a clone and `python main.py`.
Pointing an install at a specific data directory is a change to `Config` in
`src/config.py`.

### There is no default user

Every command that acts for an account requires `--user`, and there is no
fallback:

```bash
python main.py cart --user alice
python main.py product 5663 --user alice
python main.py order list --user alice
```

Commands that need no account — `user list`, `catalogue show`, `serve` — do not
take one. A default would mean a command run without arguments silently
operating on somebody's cart.

### How the session is kept

Login state lives in the database (`data/sawa9ly.db`), in the `settings` table
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

> `.env` and `data/` are both secrets and both gitignored. See
> [Security](#security-env-and-data) for how to handle them.

> Stored cookies are bound to the `sawa9ly.app` apex domain on purpose. The
> site also answers on `sawa9ly.com`, and domain-less cookies get duplicated in
> the jar, which makes Laravel read a stale session.

## Project layout

```
main.py                     CLI entry point (thin)
cli/                        one module per command group
  app.py                    builds the parser, runs the selected group
  base.py                   shared CLI helpers (Cli)
  output.py                 table / --json rendering (Output)
  product.py                product, cart and cart-line commands
  catalogue.py              saved product info
  client.py                 delivery recipients
  order.py                  orders
  account.py                users and API keys
  serve.py                  runs the HTTP API
src/
  __init__.py
  db.py                     engine, session factory, Base, init_db
  server.py                 FastAPI app, and serves the built dashboard
  schemas.py                request/response bodies
  utils/
    __init__.py             BASE_URL, COOKIE_DOMAIN, parse_cookie
    livewire.py             Livewire client, login and session persistence
    selector.py             Selector base: url + cached document + client
    passwords.py            Passwords: scrypt hash and verify
    tokens.py               Token: signed, expiring dashboard tokens
  models/
    __init__.py             re-exports the entities
    user.py                 User + Role: sawa9ly credentials, role, dashboard password
    setting.py              Setting: per-user key/value (the session lives here)
    api_key.py              ApiKey: hashed API keys
    product.py              Product: saved catalogue info
    client.py               Client: delivery recipient
    order.py                Order + OrderState
    order_line.py           OrderLine: one product on an order
    secret.py               Secret: app-wide secrets (token signing key)
  services/
    __init__.py
    product.py              Product page service
    cart.py                 Cart page service
    order.py                OrderService: draft editing and checkout
  controllers/
    __init__.py
    dependencies.py         request plumbing (Dependencies)
    products.py, cart.py, checkout.py, catalogue.py, client.py, order.py
    auth.py                 dashboard sign-in
    admin_users.py          admin: users
    admin_keys.py           admin: API keys
public/                     admin dashboard (React + Vite); only dist/ is served
data/                       SQLite database (gitignored)
AGENTS.md                   project conventions
```

## CLI

```bash
python main.py <command> [args]
```

Every command below can be written either way — `python main.py user list` from
a checkout, or `python -m sawa9ly user list` (or just `sawa9ly user list`) once
the package is installed. They are two doors onto the same parser, not two
different tools.

Results print as a table. Add `--json` (before the command) for raw JSON when
you want to pipe it into something else.

```bash
python main.py --json cart
```

### Cart and products

| Command | Description |
| --- | --- |
| `cart` | Show the cart: quantities, prices, count, total |
| `login` | Log in now, refresh the stored session, and print the cookie |
| `product <id>` | Scrape a product page |
| `cart-add <id>` | Add a product to the cart |
| `cart-remove <id>` | Remove a product from the cart (product page) |
| `cart-set-quantity <id> <qty>` | Set a cart line quantity (persisted) |
| `cart-set-price <id> <price>` | Set a cart line unit price (does not persist) |
| `cart-remove-item <id>` | Remove a cart line (cart page) |
| `checkout` | Set quantities/prices, fill the form and submit |

All of these take `--user`, and the product id is required — there is no default
for either.

```bash
python main.py product 5663 --user alice
python main.py cart-add 5663 --user alice
python main.py cart --user alice

# Checkout, staging only (never submits):
python main.py checkout --user alice --dry-run --prices '{"5663": 16000, "5724": 5000}'

# Checkout for real:
python main.py checkout --user alice \
  --quantities '{"5663": 2}' \
  --prices '{"5663": 16000, "5724": 5000}' \
  --client '{"full_name": "Jane Doe", "phone": "0555000000", "adresse": "1 Rue ...", "wilaya_id": 16, "commune_id": 1}'
```

### Catalogue, clients and orders

| Command | Description |
| --- | --- |
| `catalogue save [id]` | Scrape a product and store its info |
| `catalogue show <id>` | Show a saved product |
| `catalogue list` | List saved products |
| `client add <name> [--phone …]` | Add or update a delivery recipient |
| `client list` | List clients |
| `order create [--client <id>]` | Start a draft order |
| `order add <order> <product> [--quantity] [--price]` | Add a product to a draft |
| `order remove <order> <product>` | Remove a product from a draft |
| `order set-quantity <order> <product> <qty>` | Set a draft line's quantity |
| `order set-price <order> <product> <price>` | Set a draft line's price |
| `order checkout <order> [--dry-run]` | Submit a draft order to the site |
| `order state <order> <state>` | Move to `confirmed` or `done` |
| `order list [--state]` | List orders |
| `order show <order>` | Show an order and its lines |
| `user add/list/delete` | Manage users |
| `user set-role <name> <role>` | Make a user an `admin` (or back to `user`) |
| `user set-login-password <name> [pw]` | Set or clear a dashboard password |
| `apikey create/list/revoke` | Manage API keys |
| `track watch/unwatch/list` | Watch saved products for changes |
| `cron run/listen/status` | The scheduled tracking queue |
| `serve [--host] [--port] [--reload]` | Run the HTTP API and dashboard |

```bash
python main.py catalogue save 5663 --user alice
python main.py client add "Jane Doe" --user alice --phone 0555000000 --adresse "1 Rue ..." --wilaya-id 16 --commune-id 1
python main.py order create --user alice --client 1
python main.py order add 1 5663 --quantity 2 --price 16000
python main.py order add 1 5724 --price 5000
python main.py order show 1
python main.py order checkout 1 --user alice --dry-run   # stages, does not order
```

### Users and roles

Every user has a role, `super`, `admin` or `user`. A `user` drives its own
sawa9ly account through API keys. An `admin` manages other users and their keys
from the dashboard. A `super` is the root account, and is deliberately awkward
to manage — see below.

A user also has an optional **dashboard password**, which is unrelated to its
sawa9ly password. `--password` sets the sawa9ly one; `--login-password` sets the
dashboard one.

The super account comes from `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` in
`.env` (see [Setup](#setup)). You can also make one by hand:

```bash
python main.py user add root --role super --login-password "a long password"
```

**The dashboard can neither create a `super` nor change or delete one.** The
role is not offered in any dropdown, and the API refuses it with a 403 even if a
request is crafted by hand. An existing super is invisible to the UI's controls,
so nobody working in the dashboard can promote, demote or delete the account
that is above them. Managing a super means the environment or the CLI.

Two related guards stop the same lockout by accident: an admin cannot change
their own role, and cannot delete their own account.

To add a second administrator once a super exists, the CLI is the way in, since
the dashboard will not hand out the role:

```bash
python main.py user add ops --login-password "a good password"
python main.py user set-role ops admin
python main.py user add apiuser --email you@example.com --password ... --login-password ...
```

`user add` refuses to create an admin or super with no dashboard password, since
it could never sign in.

### Orders

An order is built in the database, so you can prepare it ahead of time and only
touch the website when you submit.

States are `draft` → `confirmed` → `done`, and **only a draft can be edited**.

`order checkout` mirrors the site's own flow: it makes the site's cart match the
order exactly (removing anything the order does not want, adding the rest at
their quantities), fills the checkout form from the order's client, and
submits. A successful submit moves the order to `confirmed` and records the
website's reference. Use `--dry-run` to do everything except the submit.

The checkout flags take JSON objects. In PowerShell wrap them in single quotes
so the inner double quotes survive.

## Python API

```python
from src.services import Cart, OrderService, Product
from src.db import session_scope

product = Product(5663)
product.get_info()          # title, availability, images, description, figures, price, categories
product.add_to_cart()       # {'product_id': 5663, 'in_cart': True}
product.remove_from_cart()  # {'product_id': 5663, 'in_cart': False}

cart = Cart()
cart.get_info()             # {'quantities': {...}, 'prices': {...}, 'count': 2, 'total': 19000}
cart.update_item_quantity(5663, 3)
cart.update_item_price(5663, 16000)
cart.remove_item(5663)
```

Each model takes an optional `client` — a `Livewire` for a specific user — so
you can drive more than one account at once. Without one they use the default
(CLI) user.

```python
from src.utils import Livewire

alice = Cart(client=Livewire("alice"))
bob = Cart(client=Livewire("bob"))
```

Mutations reload the page; call `.refresh()` to force a re-read.

## Configuration

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

**Database** — leave all unset for SQLite in `data/sawa9ly.db`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | — | A full SQLAlchemy URL; wins over everything below |
| `SQLITE_FILE` | `data/sawa9ly.db` | Where the SQLite file lives |
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

**Logging** — silent unless asked for.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | — | Also write to this file |
| `LOG_FORMAT` | `text` | `json` for one object per line |

Any log line mentioning a password, token, key or cookie has its values
replaced with `[redacted]`.

**Dashboard**

| Variable | Default | Meaning |
| --- | --- | --- |
| `DASHBOARD_SECRET` | generated once, stored in the db | Signing key for session tokens |

**Tracking queue**

| Variable | Default | Meaning |
| --- | --- | --- |
| `CRON_INTERVAL` | `300` | Seconds between passes |
| `CRON_DELAY` | `1.0` | Seconds between products inside one pass |

Set it explicitly on a server so tokens survive a database restore.

## HTTP API

**See [API_GUIDE.md](API_GUIDE.md)** for the full guide: which credential each
route wants, what every error code means, and worked workflows including placing
an order safely. This section is the summary; `/docs` is the live schema
reference.

```bash
python main.py apikey create --user local --label "my app"   # prints the key once
python main.py serve --port 8000                             # or: uvicorn src.server:app
```

Interactive docs are at http://127.0.0.1:8000/docs. Machine routes need an API
key; `/auth` and `/admin` need a dashboard token instead.

```bash
curl -H "X-API-Key: sk_..." http://127.0.0.1:8000/v1/cart
```

The key identifies the user, and every request uses that user's own sawa9ly
session and cart, so two keys never interfere.

### Versioning

The **machine-facing** routes sit under **`/v1`**:

| Route | Description |
| --- | --- |
| `GET /v1/products/{id}` | Scrape a product page |
| `POST /v1/products/{id}/cart` | Add to cart |
| `DELETE /v1/products/{id}/cart` | Remove from cart |
| `GET /v1/cart` | The cart |
| `PUT /v1/cart/items/{id}/quantity` | Set a quantity |
| `PUT /v1/cart/items/{id}/price` | Set a unit price |
| `DELETE /v1/cart/items/{id}` | Remove a line |
| `POST /v1/checkout` | Set quantities/prices, fill the form, submit |
| `GET /v1/catalogue`, `GET /v1/catalogue/{id}`, `POST /v1/catalogue/{id}` | Saved product info |
| `GET/POST /v1/clients`, `GET /v1/clients/{id}` | Delivery recipients |
| `GET/POST /v1/orders`, `GET /v1/orders/{id}` | Orders |
| `POST /v1/orders/{id}/lines` | Add a product to a draft |
| `PUT/DELETE /v1/orders/{id}/lines/{product}` | Edit or remove a line |
| `POST /v1/orders/{id}/checkout` | Submit a draft order |
| `GET/POST /v1/trackers`, `DELETE /v1/trackers` | Watched products for change tracking |

The prefix is the version of the **wire format**, not of the application, and the
two move independently — a bug fix can ship as 1.3.1 while the contract is still
`/v1`. A future `/v2` is added alongside `/v1`, never in place of it.

**Three groups are deliberately unversioned**, because nothing outside this
project consumes them:

| Route | Description | Why no version |
| --- | --- | --- |
| `GET /health` | Liveness, no auth | A load balancer or container health check is configured against a fixed path; versioning it breaks those silently |
| `GET /me` | The user the key belongs to | Meta route, not part of the resource contract |
| `/auth/*`, `/admin/*` | The dashboard's own API | The dashboard in `public/` is the only caller, so there is no second consumer to keep compatible |

The admin routes need `Authorization: Bearer <token>` from `POST /auth/login`
with an admin's username and password:

| Route | Description |
| --- | --- |
| `POST /auth/login` | Exchange username + password for a token (12h) |
| `GET /auth/me` | The signed-in user |
| `GET/PATCH /auth/me/profile` | Your own profile, any role |
| `POST /auth/me/sawa9ly-login` | Refresh your sawa9ly session |
| `GET/POST /admin/users` | List or create users |
| `PATCH/DELETE /admin/users/{id}` | Edit or delete a user |
| `GET /admin/api-keys` | Every key, every user |
| `POST /admin/users/{id}/api-keys` | Issue a key; plaintext in the response only |
| `DELETE /admin/api-keys/{id}` | Revoke a key |

A valid token for a non-admin gets 403, not 401, so a client can tell "sign in"
from "not allowed".

## Admin dashboard

A React app served by the API at the site root. It manages products, users, API
keys and your own account — orders and the cart are still driven from the CLI or
the API.

```bash
cd public
npm install
npm run build          # writes public/dist, which the API serves
```

Then open http://127.0.0.1:8000/ and sign in with a username and dashboard
password.

There is no Node at runtime: the build is static files, so the only process is
the API. `npm run dev` runs Vite on port 5173 and proxies `/v1`, `/auth` and
`/admin` (plus the unversioned `/health` and `/me`) to port 8000 for front-end
work.

**Restart both processes after changing routes or the proxy config.** Neither
picks those up on its own: routes are registered when `create_app()` runs at
import, and `vite.config.ts` is read once at startup. A stale `serve` or a stale
dev server answers with a 404, a 405, or the dashboard's own HTML — which reads
like a routing bug in the code you just changed. `API_RELOAD=true` restarts the
API on a code change, but Vite still needs stopping and starting by hand for a
config edit.

Sign in before the dashboard does anything, and note that a stored token is
re-checked against the server on every load — a token in the browser proves
nothing once it is revoked or its owner is demoted.

### Products

**Products** lists the saved catalogue. **Fetch from site** takes a sawa9ly
product id, scrapes that page and stores it — the only dashboard action that
makes the server talk to sawa9ly, so it is a deliberate form rather than a
button on every row.

Opening a product shows its details and images, with a **Track** button that
subscribes it to the tracking queue. Turning tracking on or off is a database
change and costs nothing; the queue picks the product up on its next pass.
Opening a product that is not saved yet offers to fetch it.

Watch state is per user: what you watch is yours, and another user watching the
same product is a second subscription, not a second scrape.

### My profile

Every signed-in user gets a **My profile** page, whatever their role. It is the
one part of the dashboard that is yours, and it never needs an administrator:

- your **dashboard password** — how you sign in here
- your **sawa9ly email and password** — how this account places orders
- a **Log in to sawa9ly** button, which creates or refreshes that account's site
  session. It is disabled until the account has both site credentials, and the
  page shows whether a stored session exists.

A plain user signs in and goes straight to their profile. They are not shown the
user or API-key pages, and those routes redirect them home rather than failing
with a 403.

### What each role can do

| | own profile | add users | edit / delete users | set another's sawa9ly details |
| --- | --- | --- | --- | --- |
| **super** | yes | yes | yes | yes |
| **admin** | yes | yes | no | no |
| **user** | yes | no | no | no |

An **admin** can create an account, and that is all. The new user starts with no
sawa9ly credentials and sets their own from their profile — the dashboard refuses
to write another person's site credentials, and the create form does not even
show the fields.

A **super** can edit and delete anyone except themselves, and cannot change or
delete a `super` account at all. The `super` role is never offered in a dropdown
and the API rejects it with a 403 even for a hand-crafted request; a `super` is
managed through `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` or
`python main.py user set-role`.

The whole matrix lives in `src/services/accounts.py`, and the UI follows the
server's `can_be_managed` flag rather than deciding for itself.

## Tracking product changes

A **tracker** is a subscription — "this user cares about this product" — not a
job. A separate queue decides what is actually worth fetching:

- a product **nobody tracks is never fetched**;
- a product is fetched **once per pass, however many people track it**, and every
  tracker on it is stamped afterwards. Ten users watching one product is one
  request, not ten.

```bash
python main.py catalogue save 5663 --user alice     # must be saved first
python main.py track watch 5663 --user alice
python main.py track list --user alice
python main.py track unwatch 5663 --user alice
```

When a watched product differs from what was stored, the row is updated, every
tracker on it gets `last_changed_at`, and the pass summary names the fields that
moved. Nothing records the old value — there is no change history.

### The queue

The queue is **global**: it follows every user's watches, so there is no user to
name and nothing to configure.

```bash
python main.py cron status                    # interval, delay, what is watched
python main.py cron run                        # one pass
python main.py cron listen                     # loop forever
```

Each product is fetched using the first of the people watching it who has
sawa9ly credentials, so it is checked on behalf of someone who wanted it checked.
Clients are reused within a pass, so a hundred products watched by three people
costs at most three logins.

`cron status` shows `fetchable_targets` and an `unfetchable_targets` list, so a
queue that would do nothing is visible before you run it rather than from a pass
full of errors.

`cron run` is the one to point a scheduler at; the scheduler then owns the timing
and a crash cannot leave a loop behind:

```cron
*/5 * * * * cd /path/to/Sawa9ly-API && .venv/bin/python main.py cron run
```

`cron listen` owns the loop itself, for a machine with nothing else scheduling.
`--max-passes` stops after N passes, which is how it is tested.

| Variable | Default | Meaning |
| --- | --- | --- |
| `CRON_INTERVAL` | `300` | Seconds between passes |
| `CRON_DELAY` | `1.0` | Seconds between products inside a pass |

The delay matters: the queue hits the live site once per watched product, and
going slowly is what keeps it a guest rather than a load.

Two behaviours worth knowing:

- **A failing pass exits non-zero.** A scheduler only sees the exit code, so a
  misconfigured scanner would otherwise look healthy forever while the errors sat
  unread in a summary.
- **Only one pass runs at a time**, via a lock file in `data/`. A lock left by a
  hard kill is taken over after 15 minutes.

`/v1/trackers` mirrors the CLI over HTTP and accepts either an API key or a
dashboard token. There is deliberately no route that triggers a pass — one web
request fanning out into hundreds of requests to the site is the fastest way to
get blocked.

## Checkout

```python
cart.checkout(
  quantities={'5663': 2},              # {product_id: qty}
  prices={'5663': 16000, '5724': 5000},  # {product_id: unit price}
  client={                             # order form
    'full_name': 'Jane Doe',
    'phone': '0555000000',
    'adresse': '1 Rue ...',
    'wilaya_id': 16,
    'commune_id': 1,
    'note': '',                        # optional
  },
  dry_run=False,
)
```

Returns:

```python
{
  'success': False,
  'order': None,
  'step': 2,
  'total': 37000,
  'errors': {'phone': ['حقل رقم الهاتف مطلوب.']},
}
```

Checkout is two steps on the site, and this reproduces both:

1. **Cart** → set quantities and prices, then `next_step`
2. **Form** → `full_name`, `phone`, `adresse`, `wilaya_id`, `note`, then
   `commune_id`, then `submit`

The form is Livewire component state, not a plain HTML form, so its fields are
pushed as component updates rather than typed into the page.

Required form fields: `full_name`, `phone`, `adresse`, `wilaya_id`,
`commune_id`. `note` is optional. Missing fields come back in `errors` and
nothing is ordered.

`wilaya_id` drives the `commune_id` options, so it is always sent in an earlier
dispatch than `commune_id`. Sending them together can submit a commune that is
not valid for the wilaya.

### Minimum commission

The site refuses to advance past the cart unless the order commission is at
least **5% of the total**. The default prices give zero commission, so
`next_step` rejects them:

```python
{'step': 1, 'errors': {'total_commission': ['الحد الأدنى للعمولة هو 5٪']}}
```

Supply prices high enough and the flow proceeds. `checkout` returns this in
`errors` rather than raising.

## How the site behaves (why the code looks like this)

These were established by probing the live site, and they drive the design:

- **Quantities are server-side; prices are not.** A price only ever lives in
  the Livewire snapshot, so it is gone after any reload. That is why `checkout`
  takes prices and applies them on the way to `submit`, instead of expecting
  `cart-set-price` to stick.
- **The order reads quantities from the cart and prices from the component
  state.** Pushing `products_quantity.X` as an `updates` value changes the
  on-screen mirror but not the total — so quantities are applied through the
  `+`/`-` actions (`incrementQuantity`/`decrementQuantity`), one unit per
  request.
- **`?step=2` does nothing.** The checkout step is component state, not a URL
  parameter; a fresh load always mounts at step 1.
- **A component action belongs to the *nearest* `wire:id` ancestor.** The
  add-to-cart button lives on `productaddtocart`, a child of `pages.product`.
  Sending the wrong component returns `500`.
- **Livewire reports validation failures in the snapshot's `memo`,** not as an
  HTTP error, so `checkout` reads them from there.
- **Login is not Livewire.** `/login` is an ordinary Laravel form
  (`POST /login` with `_token`, `email`, `password`), so it is a normal form
  post rather than a `/livewire/update` call.

## Caveats

- `cart-set-price` and the price part of a cart update do not persist — the
  value is only visible in the response for that request. Use `checkout`.
- Quantities are applied server-side and **persist even if the checkout later
  fails**, so a rejected checkout can still leave quantities changed. Use
  `--dry-run` to stage without submitting (quantities are still applied).
- `checkout` with a complete, valid `client` **places a real order** that cannot
  be cancelled from here. Test with incomplete `client` data to exercise the
  flow without ordering.
- Selectors are tied to the site's markup and Tailwind classes; the long
  `nth-child` chains in `Product.guide` will break if the theme is redeployed.

## Security: `.env`, `data/` and credentials

Three things hold secrets. Treat all of them as passwords.

| What | Contains | If leaked |
| --- | --- | --- |
| `.env` | your account email and password, in plain text | the account can be logged into, and the password tried elsewhere |
| `data/sawa9ly.db` | session cookies and the sawa9ly password of every user | the account can be used until the session expires, with **no password needed** |
| an API key | one user's full access to the API | that user can place orders, and read their saved data |

The session cookie is `HttpOnly` and `Secure`, so scripts running on the site
cannot read it — but it is a bearer credential: whoever holds the database can
be logged in as you.

### Passwords and keys are hashed, and shown once

An **API key** is stored as a SHA-256 hash. The plaintext is printed only in the
response that creates it, so it cannot be recovered later — if you lose it,
create another and revoke the lost one.

A **dashboard password** is stored as a scrypt hash with a per-user salt, and is
verified in constant time. It is unrelated to the sawa9ly password: one signs in
to the dashboard, the other signs in to the site.

A **dashboard token** is signed, not stored, and expires after 12 hours. There is
no token table, so a token cannot be revoked individually — changing the password
is what invalidates outstanding tokens early.

Nothing logs a credential. The only command that prints one is
`python main.py login`, which prints a cookie.

### Keep them out of git

All of them are in `.gitignore`. Confirm the rules actually apply:

```bash
git check-ignore -v .env data/sawa9ly.db
```

If any was already committed before the ignore rule existed, ignoring is not
enough — the contents stay in history. Untrack it:

```bash
git rm --cached .env data/sawa9ly.db
```

Never bypass with `git add -f`, and do not assume a `.gitignore` protects a file
that was added earlier. If a secret ever did reach a remote, rotate it (below);
rewriting history is not a substitute.

### Restrict file permissions

Only your own user account needs to read these files.

```powershell
# Windows
icacls .env                 /inheritance:r /grant:r "$env:USERNAME:(F)"
icacls data\sawa9ly.db      /inheritance:r /grant:r "$env:USERNAME:(F)"
```

```bash
# Linux / macOS
chmod 600 .env data/sawa9ly.db
```

### Do not leak them through output

`python main.py login` prints the cookie string to stdout, so it lands in
terminal scrollback and in anything you redirect that output to. Do not pipe it
into a shared file or a CI log. When reporting a problem, paste the error text —
never the contents of `.env` or the database, and not screenshots of them either.

### Prefer environment variables on servers

`.env` is a convenience for local use. On a server or in CI, set the variables
in the environment from your secret store instead — `load_dotenv()` does not
override variables that already exist, so real environment variables win and no
file is needed:

```bash
export SUPER_ADMIN_USERNAME=...
export SUPER_ADMIN_PASSWORD=...
export DASHBOARD_SECRET=...        # otherwise generated and stored in the db
export DATABASE_URL=postgresql://...
```

Only the super account's credentials are environment variables. The site's own
credentials live on the user row, set once with `user add`, so a server
deployment does not put them in the environment at all.

### Rotating if a secret is exposed

1. **Change the account password on the site.** This is the only step that
   actually protects the account; everything else is cleanup.
2. Revoke the API key: `python main.py apikey revoke <id>`. This takes effect
   immediately, even though a leaked copy of the key still works until revoked.
3. Delete the database to drop the stored session: `Remove-Item
   data\sawa9ly.db`. It is rebuilt from the site on the next run.

Deleting the database only logs out *this* installation. It does not invalidate
a copy someone already took, which is why step 1 comes first.

### Sessions expire

The stored session is time-limited, and the app logs in again automatically when
it goes. That is convenience, not security: it just means a stolen session is
only useful for as long as that session lives.

