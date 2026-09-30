# The command line

## Commands

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

## Cart and products

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

## Catalogue, clients and orders

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

## Users and roles

Every user has a role, `super`, `admin` or `user`. A `user` drives its own
sawa9ly account through API keys. An `admin` manages other users and their keys
from the dashboard. A `super` is the root account, and is deliberately awkward
to manage — see below.

A user also has an optional **dashboard password**, which is unrelated to its
sawa9ly password. `--password` sets the sawa9ly one; `--login-password` sets the
dashboard one.

The super account comes from `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` in
`.env` (see [Setup](../start/README.md#setup)). You can also make one by hand:

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

## Orders

An order is built in the database, so you can prepare it ahead of time and only
touch the website when you submit.

States are `draft` → `confirmed` → `done`, and **only a draft can be edited**.

### A worked example

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

### Things that will bite you

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

### Checking out

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

## Landing pages

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
