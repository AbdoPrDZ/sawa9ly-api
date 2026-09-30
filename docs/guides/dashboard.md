# The admin dashboard

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

## Products

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

## My profile

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

## What each role can do

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
