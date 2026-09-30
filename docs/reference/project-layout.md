# Project layout

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
database/                   SQLite database (gitignored)
data/                       working state: the lock files (gitignored)
logs/                       the five log files (gitignored)
AGENTS.md                   project conventions
```
