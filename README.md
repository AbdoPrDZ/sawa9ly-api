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
- the dashboard is not served, because `dashboard/dist` is not part of the
  distribution, so `/` returns 404 while the API routes still work;
- `serve` needs `SUPER_ADMIN_USERNAME` and `SUPER_ADMIN_PASSWORD` set, or an
  existing super in that separate database, or it refuses to start.

Read-only commands against the live site work fine. Anything that should see
your real users, keys, orders or cart wants a clone and `python main.py`.
Pointing an install at a specific data directory is a change to `Config` in
`src/config.py`.

### The default user is the super admin

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
  page.py                   landing pages
  account.py                users and API keys
  track.py                  product watches
  cron.py                   the scheduled queue
  telegram.py               the Telegram listener
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
    telegram.py             Telegram Bot API client; keeps the token out of errors
  models/
    __init__.py             re-exports the entities
    user.py                 User + Role: sawa9ly credentials, role, dashboard password
    setting.py              Setting: per-user key/value (the session lives here)
    api_key.py              ApiKey: hashed API keys
    product.py              Product: saved catalogue info
    client.py               Client: delivery recipient
    order.py                Order + OrderState
    order_line.py           OrderLine: one product on an order
    landing_page.py         LandingPage + PageState: a user page per product
    telegram_binding.py     TelegramBinding: one user's linked chat + its code
    secret.py               Secret: app-wide secrets (token signing key)
  services/
    __init__.py
    product.py              Product page service
    cart.py                 Cart page service
    order.py                OrderService: draft editing and checkout
    order_page.py           OrderPage: reads the site's own order page
    landing_page.py         LandingPageService: create, edit, move state
    tracking.py             Tracking: watches and the product scan
    order_sync.py           OrderSync: reconciles order state against the site
    telegram.py             TelegramService: binding links and incoming messages
    cron.py                 Cron: the queue's timing, locking and reporting
  controllers/
    __init__.py
    dependencies.py         request plumbing (Dependencies)
    products.py, cart.py, checkout.py, catalogue.py, client.py, order.py,
    page.py, trackers.py, telegram.py
    public_page.py          a published landing page, for anyone
    auth.py                 dashboard sign-in
    admin_users.py          admin: users
    admin_keys.py           admin: API keys
    admin_orders.py         admin: every user's orders (super only)
dashboard/                 admin dashboard (React + Vite); only dist/ is served
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
| `cart show` | Show the cart: quantities, prices, count, total |
| `cart add <id>` | Add a product to the cart |
| `cart remove <id>` | Remove a product from the cart (product page) |
| `cart set-quantity <id> <qty>` | Set a cart line quantity (persisted) |
| `cart set-price <id> <price>` | Set a cart line unit price (does not persist) |
| `cart remove-item <id>` | Remove a cart line (cart page) |
| `login` | Log in now, refresh the stored session, and print the cookie |
| `product <id>` | Scrape a product page |
| `checkout` | Set quantities/prices, fill the form and submit |

The cart's operations are nested under `cart` rather than spelled out as
`cart-add`, `cart-remove` and so on: a set of flat names that all start with the
same word is one namespace pretending to be six. This is the same shape every
other resource here uses — `order`, `client`, `page`, `catalogue`.

All of these take `--user` — optional, defaulting to the super admin as described
above — and the product id is required, with no default for it.

```bash
python main.py product 5663 --user alice
python main.py cart add 5663 --user alice
python main.py cart set-quantity 5663 2 --user alice
python main.py cart set-price 5663 16000 --user alice
python main.py cart show --user alice
python main.py cart remove-item 5663 --user alice

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
| `client add <name> --user <u> [--phone …]` | Add or update a delivery recipient |
| `client list --user <u>` | List a user's clients |
| `order create --user <u> [--client <id>]` | Start a draft order |
| `order add <order> <product> [--quantity] [--price]` | Add a product to a draft |
| `order remove <order> <product>` | Remove a product from a draft |
| `order set-quantity <order> <product> <qty>` | Set a draft line's quantity |
| `order set-price <order> <product> <price>` | Set a draft line's price |
| `order checkout <order> --user <u> [--dry-run]` | Submit a draft order to the site |
| `order state <order> <state>` | Move to `confirmed` or `done` |
| `order list --user <u> [--state]` | List a user's orders |
| `order show <order>` | Show an order and its lines |
| `page create <product> <title> --user <u>` | Start a draft landing page |
| `page list --user <u> [--product] [--state]` | List a user's landing pages |
| `page show/edit/state <page>` | Read a page, change it, move it |
| `user add/list/delete` | Manage users |
| `user set-role <name> <role>` | Make a user an `admin` (or back to `user`) |
| `user set-login-password <name> [pw]` | Set or clear a dashboard password |
| `apikey create/list/revoke` | Manage API keys |
| `track watch/unwatch/list` | Watch saved products for changes |
| `cron run/listen/status` | The scheduled tracking queue |
| `serve [--host] [--port] [--reload]` | Run the HTTP API and dashboard |

`--user` is **required** on `order create`, `order list` and `order checkout`, and on
the `client` commands, because those are the ones that have to say whose account
they are creating something in. It is **not** accepted by the line commands at
all, because an order already knows its owner — see [Orders](#orders) for a full
walkthrough. Everywhere else it may be omitted and falls back to the super admin.

```bash
python main.py catalogue save 5663 --user alice
python main.py client add "Jane Doe" --user alice --phone 0555000000 --adresse "1 Rue ..." --wilaya-id 16 --commune-id 1
python main.py order create --user alice --client 1
python main.py order add 1 5663 --quantity 2 --price 16000
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

#### A worked example

Everything below is one order, start to finish. Replace `alice` with your user and
the ids with your own.

```bash
# 1. A delivery recipient. Needed before checkout, not before editing.
python main.py client add "Jane Doe" --user alice \
  --phone 0555000000 --adresse "1 Rue Exemple" --wilaya-id 16 --commune-id 1

# 2. Start a draft. Note the "id" it prints — every later command needs it.
python main.py order create --user alice --client 1

# 3. Add lines. The ORDER id comes first, the product id second.
python main.py order add 1 5663 --quantity 2 --price 16000
python main.py order add 1 5724 --price 5000

# 4. Edit a line, or drop it.
python main.py order set-quantity 1 5663 3
python main.py order set-price    1 5663 15000
python main.py order remove       1 5724

# 5. Look before you leap.
python main.py order show 1
python main.py order list --user alice

# 6. Stage it on the site WITHOUT ordering anything.
python main.py order checkout 1 --user alice --dry-run

# 7. Only when you mean it: drop --dry-run. This places a real order.
python main.py order checkout 1 --user alice

# 8. Later, once it is confirmed, close the order off by hand.
python main.py order state 1 done
```

#### Things that will bite you

- **The order id comes first.** `order add <order> <product>`, not the other way
  round. This is the single most common mistake.
- **The line commands take no `--user`.** An order already knows its owner, so
  `order add`, `remove`, `set-quantity`, `set-price` and `state` reject the flag.
  `--user` belongs to `order create`, `order list` and `order checkout`.
- **A product appears at most once in an order.** Re-running `order add` on a
  product already in the order **tops up** its quantity instead of adding a second
  line. Use `set-quantity` when you mean to replace it.
- **Each line records the product's own price as it was when the line was
  created**, in `origin_price`, parsed from the site's display text so that
  `'14,500 دج'` becomes `14500`. It is a snapshot, so a later price change on the
  site cannot rewrite the margin an order was built at. It is set once and never
  refreshed, not even by a top-up. It is null when the product was not in the
  catalogue yet, or when its price carries no number at all - "sur demande" for
  instance. Null means unknown, not zero.
- **`<product>` is the sawa9ly product id** — the same one the catalogue uses and
  the one the site knows — not an internal row number. A product that is not in
  the catalogue yet gets an empty row created for it (`title` and `price` null)
  so the line can exist; run `catalogue save <id>` to fill in its details.
- **`checkout` needs a client.** An order with no recipient is refused, so create
  the client first or pass `--client` to `order create`.
- **Always set a price.** A line with no price contributes nothing, and the site
  has a 5% commission floor, so a checkout that only sets quantities stalls at
  step 1. `set-price` and `set-quantity` refuse anything below 1.
- **Only a draft is editable.** After a successful checkout the order is
  `confirmed` and every line command is refused. Over HTTP that is a 409; from
  the CLI it raises `OrderError`.
- **A real checkout cannot be undone from here.** Nothing in this project cancels
  an order once the site has it. Use `--dry-run` while you are learning the flow;
  it stops after staging the cart, but it does still write to the live cart, so
  put the quantities back afterwards.
- **The state machine is forward-only:** `draft` → `confirmed` → `done`, one step
  at a time, plus `draft` → `cancelled` and `confirmed` → `cancelled`. `order
  state` will not skip ahead or go backwards; asking for the state an order is
  already in is a no-op. `cancelled` is terminal, and a `done` order **cannot** be
  cancelled — an order that has run its course is finished rather than called off.
  Restoring a cancelled order means composing a new one, so the history stays
  honest.

#### Checking out

`order checkout` mirrors the site's own flow: it makes the site's cart match the
order exactly (removing anything the order does not want, adding the rest at
their quantities), fills the checkout form from the order's client, and
submits. A successful submit moves the order to `confirmed` and records two
things the site hands back: `reference`, and `origin_id`, the order number the
site generated (`879988`, say). `origin_id` is what makes the order
addressable afterwards — it is the `id` in the site's own
`/order/{origin_id}` page, which is where its current state and its lines can be
read. Use `--dry-run` to do everything except the submit. The checkout flags take
JSON objects. In PowerShell wrap them in single quotes so the inner double
quotes survive.

### Landing pages

A landing page is **one user's writing about one product**. Users do not see each
other's pages, and a single user may keep as many pages for the same product as
they like — a seasonal offer, a second language, a variant.

| Field | Meaning |
| --- | --- |
| `id` | the page's own key — **never** used in a public URL |
| `user_id` | whose page it is; pages cascade away with the user |
| `product_id` | our own `products.id`, which is what the page is stored against |
| `public_id` | the opaque token the page is served under |
| `title` | what the page is called in the list |
| `html` | the markup, stored exactly as written |
| `state` | `draft`, `publish` or `archive` |

The state is a label for the page, and it decides exactly one thing: **only
`publish` is served.** A `draft` or an `archive` 404s at its public address, and
so does a token that matches nothing — the three are indistinguishable, so an
unpublished page's URL leaks nothing, not even that it exists.

## Publishing a page

A published page is served at **`/pages/{public_id}`**:

```text
http://127.0.0.1:8000/pages/7d_3zlLqxz0DZ6k2RiaKzg
```

```bash
python main.py page create 5663 "Summer offer" --html "<h1>Summer</h1>" --user alice
python main.py page list --user alice
python main.py page state 1 publish      # now it is served
```

`public_id` is 22 URL-safe characters of randomness, unique across **every**
user's pages, and unrelated to the row `id` — which is ours and enumerable, so it
must never appear in a public address. The dashboard shows the full link on the
**Pages** list and in the edit dialog, and only makes it clickable once the page
is published.

Note the two things called "pages", which are deliberately different resources
behind different credentials:

| Path | What it is |
| --- | --- |
| `/pages/{public_id}` | the **public** page, as HTML, for anyone with the link. No sign-in. |
| `/api/v1/pages`, `/api/v1/pages/{id}` | the signed-in user's **own** pages, as JSON. Dashboard token or API key. |

The public route is a catch-all registered **last**, so a request for an API
route, a dashboard route or `/docs` is matched before it ever gets there.
`/pages` with no id is a 404, and the app's own Pages page lives at
`/dashboard/pages`, so the two cannot collide.

In development, `npm run dev` proxies `/pages` to the API along with `/api`. That
matters: the link the dashboard shows is built from `window.location.origin`, so
in dev that is port 5173, and Vite would otherwise refuse it with a "public base
URL" error. With the proxy, a published page is reachable on `localhost:5173` and
on `localhost:8000` alike, so dev behaves like production. **Restart
`npm run dev` after changing `vite.config.ts`.**

A public address that serves no page answers **404 with a plain page**, not the
API's JSON: these URLs are followed by people, not clients. That covers a page
that was never published, one that has been archived, one whose token is wrong
and the bare /pages — all four look the same, so an unpublished page leaks
nothing, not even that it exists. The root / does the same and points at the
dashboard. Anything under /api still answers JSON, because that is what its
callers parse.

### The sandbox header, and why it is not decoration

The dashboard and the published pages share an origin, and the dashboard keeps
its session token in `localStorage`. So a served page is sent with:

```text
Content-Security-Policy: sandbox
X-Content-Type-Options: nosniff
Cache-Control: no-cache
```

Without `sandbox`, any script in a published page runs on that same origin and
can read that token — so a page an administrator visited would hand over their
session. `sandbox` gives the page a unique, opaque origin with no script
execution: HTML and CSS render as written, and the dashboard's origin is
unreachable from the page.

**The cost is that a page cannot run its own JavaScript.** If you need that, the
fix is to serve pages from a *different origin* — a second port or host is a real
origin boundary — not to loosen the header. Do not add `allow-scripts` while
pages and the dashboard share an origin.

**Two product ids, as everywhere.** You *create* a page by the **sawa9ly**
product id, because that is the id you have. It is stored against our own
`products.id`, and `PageOut` returns both — `product_id` (ours) and
`sawa9ly_product_id` (the site's) — so nothing downstream has to guess.

```bash
python main.py page create 5663 "Summer offer" --html "<h1>Summer</h1>" --user alice
python main.py page create 5663 "Winter offer" --user alice      # a second page, same product
python main.py page list --user alice
python main.py page list --user alice --product 5663
python main.py page list --user alice --state publish
python main.py page edit 1 --html "<h1>Summer sale</h1>"          # markup only
python main.py page state 1 publish
python main.py page show 1
```

From the dashboard: **Pages**, available to every signed-in user, lists and edits
yours and creates new ones. A product that is not in the catalogue yet is fine —
the row is created for it, the same as when you add one to an order.

**The markup is stored verbatim.** See [Publishing a page](#publishing-a-page)
for how it is served and why the response is sandboxed.

### Clients and pages are yours alone

`/api/v1/clients` and `/api/v1/pages` are scoped to the caller, and there is no
admin or super-wide view of either. A `super` asking for another user's page gets
the same 404 as anyone else. The only cross-user order view in the project is
`/api/admin/orders`, which is super-only on purpose.

Neither resource has a delete. A client is corrected by saving the same name
again, and a page is corrected by editing it, but neither can be removed from the
UI — add a `DELETE` route and a control if you want that.

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

**Logging** — on by default, one file per subsystem under `data/logs/`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_DIR` | `logs` | Where the five log files go |
| `LOG_FILE` | — | One file receiving everything, instead of the five |
| `LOG_FORMAT` | `text` | `json` for one object per line |

The five files, and what lands in each:

| File | Holds |
| --- | --- |
| `sawa9ly-api.log` | the API, the site scraper, and the HTTP access log |
| `sawa9ly-dashboard.log` | browser requests for the dashboard and published pages |
| `sawa9ly-cli.log` | which command ran, for which account, and whether it worked |
| `sawa9ly-cron.log` | the queue: tracking, order sync, notifications |
| `sawa9ly-telegram.log` | the bot |

A file appears the first time something is written to it, so a quiet day leaves
none behind. Everything also goes to the console, as before.

`INFO` rather than `WARNING` is the default because the queue and the bot run in
the background: their pass summaries are the only record that they ran at all. The
HTTP access log stays at `INFO` whatever `LOG_LEVEL` is set to — it is the api
log's reason for existing, and turning the level up to quiet the rest should not
delete the traffic history too.

Any log line mentioning a password, token, key or cookie has the value replaced
with `[redacted]`, whether the value was passed as an argument or already built
into the string.

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
key; `/api/auth` and `/api/admin` need a dashboard token instead. `/api/v1/orders` and
`/api/v1/trackers` take either, because the dashboard reads them too.

```bash
curl -H "X-API-Key: sk_..." http://127.0.0.1:8000/api/v1/cart
```

The key identifies the user, and every request uses that user's own sawa9ly
session and cart, so two keys never interfere.

### Versioning

The **machine-facing** routes sit under **`/api/v1`**:

| Route | Description |
| --- | --- |
| `GET /api/v1/products/{id}` | Scrape a product page |
| `POST /api/v1/products/{id}/cart` | Add to cart |
| `DELETE /api/v1/products/{id}/cart` | Remove from cart |
| `GET /api/v1/cart` | The cart |
| `PUT /api/v1/cart/items/{id}/quantity` | Set a quantity |
| `PUT /api/v1/cart/items/{id}/price` | Set a unit price |
| `DELETE /api/v1/cart/items/{id}` | Remove a line |
| `POST /api/v1/checkout` | Set quantities/prices, fill the form, submit |
| `GET /api/v1/catalogue`, `GET /api/v1/catalogue/{id}`, `POST /api/v1/catalogue/{id}` | Saved product info |
| `GET/POST /api/v1/clients`, `GET /api/v1/clients/{id}` | Delivery recipients |
| `GET/POST /api/v1/pages`, `GET/PATCH /api/v1/pages/{id}` | Landing pages, one per user |
| `GET/POST /api/v1/orders`, `GET /api/v1/orders/{id}` | Orders |
| `POST /api/v1/orders/{id}/lines` | Add a product to a draft |
| `PUT/DELETE /api/v1/orders/{id}/lines/{product}` | Edit or remove a line |
| `POST /api/v1/orders/{id}/checkout` | Submit a draft order |
| `GET/POST /api/v1/trackers`, `DELETE /api/v1/trackers` | Watched products for change tracking |

The prefix is the version of the **wire format**, not of the application, and the
two move independently — a bug fix can ship as 1.3.1 while the contract is still
`/api/v1`. A future `/v2` is added alongside `/api/v1`, never in place of it.

**Three groups are deliberately unversioned**, because nothing outside this
project consumes them:

| Route | Description | Why no version |
| --- | --- | --- |
| `GET /api/health` | Liveness, no auth | A load balancer or container health check is configured against a fixed path; versioning it breaks those silently |
| `GET /api/me` | The user the key belongs to | Meta route, not part of the resource contract |
| `/api/auth/*`, `/api/admin/*` | The dashboard's own API | The dashboard in `dashboard/` is the only caller, so there is no second consumer to keep compatible |

The admin routes need `Authorization: Bearer <token>` from `POST /api/auth/login`
with an admin's username and password:

| Route | Description |
| --- | --- |
| `POST /api/auth/login` | Exchange username + password for a token (12h) |
| `GET /api/auth/me` | The signed-in user |
| `GET/PATCH /api/auth/me/profile` | Your own profile, any role |
| `POST /api/auth/me/sawa9ly-login` | Refresh your sawa9ly session |
| `GET/POST /api/admin/users` | List or create users |
| `PATCH/DELETE /api/admin/users/{id}` | Edit or delete a user |
| `GET /api/admin/api-keys` | Every key, every user |
| `POST /api/admin/users/{id}/api-keys` | Issue a key; plaintext in the response only |
| `DELETE /api/admin/api-keys/{id}` | Revoke a key |
| `GET /api/admin/orders` | **Super only.** Every user's orders, not filtered by user |
| `GET /api/admin/orders/{id}` | **Super only.** One order, whoever owns it |

A valid token for a non-admin gets 403, not 401, so a client can tell "sign in"
from "not allowed". `/api/admin/orders` asks for the `super` role specifically, so an
`admin` gets 403 there too — it is the one route that crosses user boundaries.

## Admin dashboard

A React app served by the API at **`/dashboard/`**. It manages products, users,
API keys and your own account, and shows your own orders read-only. Building and
placing an order is still done from the CLI or the API, because a checkout places
a real order on the site.

```bash
cd dashboard
npm install
npm run build          # writes dashboard/dist, which the API serves
```

Then open http://127.0.0.1:8000/dashboard/ and sign in with a username and dashboard
password.

There is no Node at runtime: the build is static files, so the only process is
the API. `npm run dev` runs Vite on port 5173 and proxies `/api` to port 8000 for
front-end work. In dev the app is at http://127.0.0.1:5173/dashboard/ , with the
same prefix it has in production.

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

| | own profile | own Telegram chat | add users | edit / delete users | set another's sawa9ly details |
| --- | --- | --- | --- | --- | --- |
| **super** | yes | yes | yes | yes | **no** |
| **admin** | yes | yes | yes | no | no |
| **user** | yes | yes | no | no | no |

**Nobody can set another user's sawa9ly credentials, at any role.** They belong to
the user, who enters them on their own profile, and an administrator who could
type them in could also sign in as that user on the site. An admin's job here is
the account and the dashboard password to reach it with; the create and edit
forms do not show the sawa9ly fields, and the API has no such fields to send.

What an admin *can* see is whether a user has set them —
`has_sawa9ly_credentials`, rendered as "set" or "not set" — which is what you need
to answer "why is this account not placing orders". Not the address itself. The
same applies to Telegram: a super sees which chat a user linked, and nobody sees
another user's chat from the admin area.

A **super** can edit and delete anyone except themselves, and cannot change or
delete a `super` account at all. The `super` role is never offered in a dropdown
and the API rejects it with a 403 even for a hand-crafted request; a `super` is
managed through `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` or
`python main.py user set-role`.

The whole matrix lives in `src/services/accounts.py`, and the UI follows the
server's `can_be_managed` flag rather than deciding for itself.

## Telegram notifications

A user can link a Telegram chat to their account and be reached there. Nothing
else in the project depends on it: with no `TELEGRAM_BOT_TOKEN` set, the whole
feature is simply off.

### Linking a chat

The link is on the user's own **My profile** page, and it is shown once.

1. The dashboard issues a **single-use code**, 10 characters, valid for 15
   minutes, stored only as a SHA-256 digest — so the code cannot be read back out
   of the database, only reissued.
2. It is handed over as a `t.me` link carrying that code. Opening the link
   delivers `/start <code>` to the bot, so there is nothing to type and nothing to
   mistype.
3. `python main.py telegram listen` receives it, checks the code, and stores the
   chat id against that user.
4. The bot replies, so a user who sent the code and heard nothing knows something
   went wrong.

What the code proves is two things at once: that the sender can post in that chat,
and that they were allowed to claim that account. A chat id on its own proves
neither — it is just a number Telegram hands out, readable off a screenshot.

**On the page, press "Open in Web" — not "Start Bot".** The link's page has two
buttons and the obvious one is the one that fails. "Start Bot" hands off to the
Telegram app through the `tg://` scheme; on a computer with no app installed
Chrome reports *"Failed to launch 'tg://resolve?…' because the scheme does not
have a registered handler"* and the button does nothing at all, silently.
"Open in Web" carries the same code in a `tgaddr` fragment and works with no app
installed. The code is on the same page too, and the bot takes it as a message
from the app or from **web.telegram.org** — bare, in backticks, in lower case, or
after `/start`. A sentence containing a code is refused on purpose, so ordinary
chatter cannot bind a chat by accident.

A **private chat with the bot** needs no setup at all. A **private channel** works
too, but the bot must be added as an admin of it, and because a channel is
broadcast-only you must be an admin as well to post the code. A **group is
refused** — it is shared with people who are not this user, so `chat_type` is
checked in the database, not just in the UI.

Issuing a new link does not unbind an existing chat, so a code that is never used
costs the user nothing. One chat belongs to one account, enforced by a
`UNIQUE(chat_id)`, so two users cannot claim the same channel.

### The listener

```bash
python main.py telegram listen                    # forever
python main.py telegram listen --max-updates 5    # stop after 5, for testing
```

It **polls** rather than taking a webhook, which is why it needs no public
address, no TLS certificate and no domain: it dials Telegram, and Telegram never
dials back. ngrok, a DDNS name and a real domain are all unnecessary here.

Two consequences worth knowing:

- **The bot is deaf while the listener is stopped.** Telegram holds undelivered
  updates for up to 24 hours, so a code sent in the meantime is delivered when it
  next starts — but nothing arrives while it is down.
- **Only one listener may run at a time.** Telegram allows one `getUpdates` per
  token and answers a second poller with a 409 on *every* poll, so a lock file
  refuses the second process up front instead. A 409 is also treated as transient
  and backed off, because Telegram keeps a token's poll state for a minute or so
  after a poller exits — so a listener restarted too quickly recovers by itself.

The offset is held in memory and starts unset, which is what lets a restart pick up
whatever was queued. A restart therefore replays up to 24 hours of updates, which
is harmless: codes are single-use, so a replayed one is refused cleanly and the
sender is told why.

### Checking a link works

```bash
python main.py telegram test --user alice      # send a test message
```

This sends a message you asked for, so it is also the quickest way to find out
that a chat works — that the bot is not muted, and that the token is still valid —
without waiting for something worth being told about.

It exits non-zero when it cannot send, so it works as a check in a script:
`telegram test --user alice && echo delivered` means what it looks like. A user
with no linked chat is an `error:` naming the dashboard page that fixes it, and a
chat the user has since blocked comes back as Telegram's own 403 reason.

### What gets a notification

One kind of event, for now: **a watched product changed**. When the queue fetches
a product and finds that its stock or its price is different from what is stored,
everyone watching that product is told. See
[`.agents/context/domains/notifications.md`](.agents/context/domains/notifications.md)
for how the record and its delivery are kept.

### The token

The Bot API puts the token in the URL of every call, so `requests` and `urllib3`
quote it in their error messages. `src/utils/telegram.py` keeps it in one private
attribute, strips it from every error that leaves the module, and has a `__repr__`
that cannot leak it. The project's log filter does **not** cover this: it redacts a
record only when the message contains a word like `token` or `secret`, and a real
token contains neither.

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

A pass runs two jobs, and both are reported:

| Job | What it does |
| --- | --- |
| `tracking` | refreshes watched products, stamps the trackers that cared |
| `orders` | re-reads each posted order's own page and reconciles our state |

Each product is fetched using the first of the people watching it who has
sawa9ly credentials, so it is checked on behalf of someone who wanted it checked.
Clients are reused within a pass, so a hundred products watched by three people
costs at most three logins.

#### The orders job

For every order that has an `origin_id` and is not already `done` or
`cancelled`, the pass reads the site's own page for it
(`src/services/order_page.py`) and moves our state to match. So an order you
cancelled on the site becomes `cancelled` here, and nobody has to retype it.

Two deliberate limits, both because `cancelled` is terminal and a wrong read
could not be undone by running the pass again:

- **Only `cancelled` is applied.** It is the one state the site has actually been
  seen to report. Any other wording is left alone and reported as a *disagreement*
  in the pass summary, rather than guessed at from a translation.
- **A refused move is reported, not forced.** If the site says `cancelled` but
  ours is `done`, the state machine forbids the move, so the summary says so and
  the order stays put.

An order with no `origin_id` is skipped — there is no page to read. That includes
any order placed before the id was recorded, which therefore needs the id filling
in by hand.

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

`/api/v1/trackers` mirrors the CLI over HTTP and accepts either an API key or a
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
  `cart set-price` to stick.
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

- `cart set-price` and the price part of a cart update do not persist — the
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

