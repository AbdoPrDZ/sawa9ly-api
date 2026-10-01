# Admin Dashboard

A React single-page app for admins: manage users and API keys, and read your own
orders. It is the only front end that talks to `/api/auth` and `/api/admin`; everything
else in the API is designed for machine callers.

## Source layout

One file per thing, matching the project's rule.

```text
src/
  main.tsx                 mounts React and the router
  App.tsx                  login / not-admin / app switch
  styles.css               the only stylesheet
  api/
    types.ts               response shapes
    client.ts              fetch wrapper, token store, ApiError
    session.ts             login, me
    profile.ts            getProfile, updateProfile, sawa9lyLogin
    catalogue.ts          listProducts, getProduct, saveProduct
    orders.ts             listOrders, getOrder
    trackers.ts            listTrackers, watch, unwatch
    telegram.ts           getBinding, issueLink, unbind
    users.ts               listUsers, createUser, updateUser, deleteUser
    keys.ts                listKeys, createKey, revokeKey
    clients.ts             listClients, createClient
    pages.ts               listPages, getPage, createPage, updatePage
  session/
    context.ts             the Session type and React context
    SessionProvider.tsx    holds the user, restores and signs in
    useSession.ts          the hook pages use
  components/              Banner, Field, Modal, OrderStateBadge, PageStateBadge,
                            RoleBadge, KeyState, Spinner, TopBar, WatchButton,
                            FetchProduct
  features/
    users/                 CreateUserModal, EditUserModal, DeleteUserModal
    keys/                  IssueKeyModal, RevokeKeyModal, RevealKeyModal
    clients/               CreateClientModal
    pages/                 CreatePageModal, EditPageModal
    telegram/              TelegramCard
  pages/                   Login, Users, ApiKeys, Profile, Products,
                            ProductDetail, Orders, OrderDetail, Clients, Pages
```

`api/` is split by resource and `features/` by the flow it belongs to, so a new
endpoint or a new modal is a new file rather than an addition to a shared one.
The UI never calls `fetch`; it goes through `api/`, which is the only place that
attaches a token or turns an error into a message.

## What is served, and from where

```text
dashboard/                  source; never served
  src/                      app code
  assets/                   favicon.ico, logo.png — copied to the build as-is
  dist/                     build output; the only part served
  vite.config.ts            build config and the dev proxy
```

The API mounts **`dashboard/dist` only**, under **`/dashboard/`**. The source,
`node_modules` and `package.json` are never exposed. Do not change the mount to
`dashboard/`.

The site is split into three namespaces, and which one a path starts with decides
who answers it:

| Prefix | Answers | Notes |
| --- | --- | --- |
| `/api/...` | the API | `/api/v1` is the machine contract, `/api/auth`, `/api/keys` and `/api/admin` the dashboard's own |
| `/dashboard/...` | this app | assets at `/dashboard/assets`, every other path the shell |
| `/pages/{public_id}` | a published landing page | HTML for anyone with the link; a catch-all registered **last**. `/pages` bare and the root both 404 with a **page**, not JSON |

Consequences worth remembering:

- The build directory is `assets`, not Vite's default `static`, because the
  server mounts `/dashboard/assets`. Renaming it in `vite.config.ts` breaks asset
  loading.
- `publicDir` is set to `assets`, which is where `favicon.ico` and `logo.png`
  live. Vite's default is `public/`, which this project does not have, so without
  that setting the folder would be read by nothing. Vite copies a publicDir's
  **contents** to the root of `outDir`, so the two land at
  `dist/favicon.ico` and `dist/logo.png` and are served as
  `/dashboard/favicon.ico` and `/dashboard/logo.png` — **not**
  `/dashboard/assets/...`, because `assets` is the publicDir itself rather than a
  folder inside it. Their names are deliberately unhashed: browsers cache
  favicons hard, and a hashed name would change on every build.
- The top bar's logo path is built from `BASENAME` in `api/client.ts`, so the
  prefix is not written out a fourth time.
- The `<link rel="icon">` in `index.html` is written as `href="/favicon.ico"` —
  from the site root, with **no** `%BASE_URL%` and no prefix of its own. Vite
  puts the base in front of it in both dev and build, so the browser asks for
  `/dashboard/favicon.ico` either way. Adding the prefix by hand doubles it: dev
  sent `/dashboard/dashboard/favicon.ico`, because the dev server rewrites that
  tag too. Do not "fix" this by prefixing it.
- **`/dashboard` is written down in three places** and they must agree:
  `DASHBOARD_BASE` in `src/server.py`, `base` in `dashboard/vite.config.ts`, and
  `BASENAME` in `dashboard/src/api/client.ts` (read by the router in
  `main.tsx`). `base` is what makes the built asset URLs `/dashboard/assets/...`;
  `BASENAME` is what makes an in-app route `/dashboard/orders`. Because
  `basename` is set, every `<Route>` and `<Link>` stays relative — `/orders`
  means `<basename>/orders` — so nothing else in the app refers to the prefix.
- The shell fallback is scoped to `/dashboard/`, **not** the whole site. A
  catch-all across the site would answer every unknown path — a mistyped API
  route — with `index.html`, which is what previously made a missing endpoint look
  like an empty 200. The one root-level catch-all that does exist is
  `PublicPageController`, and it answers only for a published page's
  `public_id`.
- `dist/` is a build artifact and is gitignored. It is rebuilt, not committed.
- A path under `/dashboard/` that names a real file is served as that file, so a
  missing asset is a 404 rather than HTML with a 200.
- A resolved path is checked to be inside `dist/` before being served, which is
  what stops `../` from walking out of the build.

## Building and running

```bash
cd dashboard
npm install
npm run dev      # Vite on :5173, serving /dashboard/ and proxying /api to :8000
npm run build    # writes dist/
npm run typecheck
```

In dev the app is at http://127.0.0.1:5173/dashboard/ — the same prefix it has in
production, because `base` applies to the dev server too.

The dev proxy forwards two prefixes: `api`, and **`pages`**. The second is not
optional polish. `publicUrl()` builds a page's address from
`window.location.origin`, so in development that is port 5173 — and Vite only
serves under its own `base`, so without the entry the link the dashboard shows
would point at the dev server and be refused with a "public base URL" error. With
it, a published page is reachable on both ports, so dev matches production.

A proxy key matches from the root, so `/pages` cannot swallow the app's own
Pages screen: that is `/dashboard/pages`.

There is no Node at runtime. The dashboard is static files; the only process is
uvicorn. `npm run dev` is for front-end work and needs the API running
separately.

The API works with no build at all — the mount is skipped when `dist/` is
absent, so a backend-only change never requires `npm install`.

## Splitting the front end

The same one-thing-per-file rule as the Python side, in practice:

- one React component per file — `components/` and `features/` hold one each, and
  there is no `ui.tsx` of small pieces;
- `api/` split per resource rather than one client for the whole project, so a
  new resource does not grow an existing module;
- `api/types.ts` kept apart from `api/client.ts`, because a response shape and
  the transport change for different reasons.

A page owns data and state. The modals it opens live in `features/`, and the
small presentational pieces live in `components/`. If a page starts containing a
form's markup, that form belongs in its own file.

## Why the paths are relative

The bundle contains no API host. It calls `/api/auth/login`, not
`http://127.0.0.1:8000/api/auth/login`, because the dashboard is served from the
same origin as the API. That is what removes the need for CORS configuration
and for any environment-specific build variable. **Do not introduce
`import.meta.env.VITE_API_URL` or a base URL** unless the dashboard is genuinely
served from a different origin than the API.

The `/api` base and the version prefix are applied in exactly one place, `urlFor`
in `dashboard/src/api/client.ts`, called from `request()`. The per-resource
modules pass **bare** resource paths (`request('/auth/me')`) and stay
prefix-agnostic, so a `/v2` is that one constant rather than an edit to every api
module. `UNVERSIONED` in the same file lists the bare prefixes that skip the
version — `/auth` and `/admin` — and must be matched against the *caller's* path,
not the resolved one.

`UNVERSIONED` in the same file is the deliberate exception: the dashboard's own
`/api/auth` and `/api/admin` are mounted unversioned on the server, because this
app is their only caller. **The server is the authority** — the list in
`client.ts` is the client half of the same fact, and the two must agree. Adding a
new dashboard-only endpoint means adding it to both.

The dev proxy exists only to reproduce same-origin behaviour locally. Its list in
`vite.config.ts` is now the single prefix `api`, which covers `/api/v1`,
`/api/auth`, `/api/admin`, `/api/health` and `/api/me` at once — so a new
endpoint under any of them is forwarded without touching that file.

The page routes in the table below are **relative to `/dashboard`**. The old
`/products` collision is gone for a stronger reason than versioning: the API's
scrape routes are `/api/v1/products/{id}` and the dashboard is under a prefix of
its own, so the two no longer share a namespace at all.

## Pages and who sees them

Every route below is relative to the `/dashboard` basename.

| Route | Page | Who |
| --- | --- | --- |
| `/profile` | `ProfilePage` | every signed-in user |
| `/products` | `Products` | every signed-in user |
| `/products/:productId` | `ProductDetail` | every signed-in user |
| `/orders` | `Orders` | every signed-in user |
| `/orders/:orderId` | `OrderDetail` | every signed-in user |
| `/clients` | `Clients` | every signed-in user |
| `/pages` | `Pages` | every signed-in user |
| `/users` | `Users` | administrators |
| `/keys` | `ApiKeys` | every signed-in user |

**A plain user is not locked out.** They get the same shell with only their
profile, their language and their own API keys, because managing their own
account is not something an administrator should have to unlock. `Sidebar` omits the admin link
for them, and `/users` redirects to `/profile` rather than letting a request
fail with a 403.

`/keys` is on the self-service list deliberately. A key is the caller's own
credential, so every account mints and revokes its own without an admin in the
room. The page adapts to the role rather than hiding: an admin lists every user's
keys and a plain user only their own (the `User` column goes away with the wider
view), and only a `super` is offered the picker to issue a key in somebody else's
name. That last one is a real permission, not a UI choice — see
`domains/authentication.md`.

The profile page is the self-service surface: the dashboard password, the
sawa9ly email and password, and a **Log in to sawa9ly** button that creates or
refreshes that account's site session. The button is disabled until the account
has both site credentials, and the page shows whether a stored session exists.

It also holds `TelegramCard`, the only place a user links a Telegram chat. The
link is fetched from `POST /api/v1/telegram/link` and shown **once**, because the
code in it is stored only as a hash — the same contract `RevealKeyModal` follows.
The card says plainly that nothing happens until `python main.py telegram listen`
is running, because that is the failure a user cannot diagnose from the page.

A user's own sawa9ly and Telegram settings are here and **nowhere else**: the
create and edit user modals do not render the sawa9ly fields at all, and the
`AdminUser` shape has no `sawa9ly_email`. The users table shows
`has_sawa9ly_credentials` as "set"/"not set" and `telegram_chat_id`, which is the
fact an operator needs and not the value.

## Products

`Products` lists the saved catalogue and is the landing page for an admin. It has
one control that reaches the site: **fetch a product by its id**, which scrapes
the page and stores the result. That is a deliberate form, not a button on every
row, because it is the only dashboard action that makes the server talk to
sawa9ly.

`ProductDetail` shows one product with an image gallery, and a `WatchButton` that
starts or stops tracking it. It handles the "not saved yet" case by offering the
same fetch, because a 404 on a product page is otherwise a dead end.

Both pages read the watch state from `/api/v1/trackers` once and match by
`product_id`, rather than asking per row. `WatchButton` re-reads the server's
answer after a failed toggle instead of keeping whatever the failed attempt
intended — the server is the truth about what is watched.

The catalogue routes take **no authentication at all**, including the POST that
scrapes. That predates the dashboard and is left alone deliberately, but the
dashboard makes it easier to reach, so it is worth an access rule before this is
exposed to anyone.

## Orders

`Orders` and `OrderDetail` are **read-only**, and that is a deliberate limit, not
an unfinished page. `/api/v1/orders` can edit lines and check out, and checkout places
a real order on the site that cannot be withdrawn from here — see
`domains/checkout.md`. So building and placing an order stays with the CLI and
the API, and the dashboard only reports what already happened.

Both read `/api/v1/orders`, which means they are one of the places the dashboard
calls a `/api/v1` route that is **not** the open catalogue. Those handlers use
`Dependencies.get_any_user`, so they accept a dashboard token as well as an API
key. This is the same either-credential arrangement `/api/v1/trackers` and
`/api/v1/clients` have, and it is safe for the same reason: every order handler is
scoped to `order.user_id == caller.id`, so neither credential reaches another
user's orders. `/api/v1/cart`, `/api/v1/checkout` and `/api/v1/products` stay
API-key only.

**A `super` sees every user's orders.** `Orders` calls `/api/admin/orders` and
`OrderDetail` calls `/api/admin/orders/{id}` when `user.role === 'super'`, and both
fall back to `/api/v1/orders` otherwise. That is the only place the dashboard branches
on `super` rather than `is_admin`, because it is the only place the answer spans
more than one user. The rule is server-side: those routes use
`Dependencies.require_super`, so an `admin` gets 403 and the UI's version check is
a convenience, not the control.

The all-users listing adds a **User** column and the detail page an **Ordered by**
row, because a list spanning users is unreadable without them. `OrderOut` carries
`username` as an optional field, set only by the admin route — the per-user routes
omit it, where it would be redundant.

`/api/v1/orders` stays caller-scoped **even for a `super`**: it answers "my orders",
and a super's own orders are the ones it returns. Do not relax that to make the
dashboard simpler; the all-users view is what `/api/admin/orders` is for.

A line's `product_id` is the **sawa9ly** id, so it links straight to
`/products/:productId`. A `null` price means the price was never set, which is
rendered as `—` and is not the same as zero. `OrderStateBadge` colours the three
states; which state an order may move to is the server's decision, never the UI's.

The lines table carries **Origin price immediately before Price**, so the margin
the line was built at is readable across two columns without arithmetic. A null
`origin_price` is styled `muted` as well as showing `—`, because it means *never
known* — the product was not in the catalogue when the line was created — rather
than a number that happens to be missing. See `domains/orders.md` for the
snapshot rule that makes the column stable.

## Clients and pages

`Clients` and `Pages` are both **self-service**: every signed-in user gets them,
and each sees only their own rows. A client and a page belong to the account
that will use them, so neither is an administrator's privilege — and unlike
`/api/admin/orders`, there is no super-wide view of either. A super asking for
another user's page or client gets a 404, the same as anyone else.

`Clients` has no delete route, so a recipient can be corrected by saving the same
name again but cannot be removed from the UI. `Pages` has list, create and edit
but likewise no delete. Both are deliberate: a delete was not asked for, and
adding one is a route plus a control.

`Pages` stores a page's markup and serves it publicly at `/pages/{public_id}`
when its state is `publish`. That is the only consumer of the state field, and
the reason it exists. `Pages` shows the full public link, but only makes it
clickable once the page is published — a draft's address 404s, so a link to it
would look broken.

**Two different things are called "pages", and they must not be confused.**
`/api/v1/pages` is the signed-in user's own pages as JSON, addressed by row id
and behind a credential. `/pages/{public_id}` is the public page as HTML, for
anyone with the link, behind nothing. The app's own Pages page is at
`/dashboard/pages`, which is a third thing again.

**The served response is sandboxed, and that is a security control, not styling.**
The dashboard and a published page share an origin, and the dashboard keeps its
token in `localStorage`, so a page that could run script on that origin could
steal the token of anyone who visited it. `Content-Security-Policy: sandbox`
gives the page an opaque origin and blocks script execution. **Never add
`allow-scripts` while pages and the dashboard share an origin** — a second port
or host is the real fix. See `src/controllers/public_page.py` for the full note.

**Human-facing URLs answer with a page; `/api` answers with JSON.** A dead
public URL, a bare `/pages` and the root all return 404 as HTML, because those
are URLs a person types. Raising `HTTPException` there would hand a reader
`{"detail": "Not found."}`. The API's own 404s stay JSON, because its callers
parse them. All four public cases are deliberately identical, so an unpublished
page's address reveals nothing.

`EditPageModal` sends only the fields that changed, because the API treats an
absent key as "leave it alone". That matters most for `html`: clearing the box
sends `""`, which really does empty the page, while never touching it sends
nothing. The two are different and the form has to keep them different.

**The two product ids again.** A page is stored against our own `products.id`,
but it is created by sawa9ly id and displayed by it, so `PageOut` carries both
`product_id` (ours) and `sawa9ly_product_id`. The page table links on the latter.
Getting this backwards is the project's most common bug — see
`domains/orders.md`.

## What each role sees

The UI follows the server's rules rather than duplicating them loosely:

- A **non-super** admin's users table has no Edit or Delete column at all, and
  the create form says the new user sets their own sawa9ly details. A banner
  states the limit. Hiding a control beats disabling it with an explanation when
  the answer is "only a super can".
- A **super** sees the full table, with Edit and Delete disabled for a `super`
  row and for their own account.
- The create form's sawa9ly email field renders a note instead of an input for a
  non-super, since the server would reject it anyway.

`can_be_managed` on a user row is what drives this. It is a server-provided flag
rather than a client guess, so the UI cannot disagree with the API.

## Credentials and the token

The dashboard signs in with `POST /api/auth/login` and stores the returned token in
`localStorage`. That token is not an API key and is not interchangeable with one;
see `domains/authentication.md` for how the two differ.

Two rules the code follows, both of which are easy to break:

- **A stored token is re-checked against the server before anything is
  rendered.** A token in `localStorage` proves nothing — it may have expired, or
  the user may have been demoted or deleted since. The app shows a spinner until
  `/api/auth/me` answers, which is also why a reload does not flash the login screen
  at an admin who is still signed in.
- **A 401 or 403 clears the token and returns to the login screen**, in one place
  (`invalidate` on the session), rather than each page handling it.

## Editing a user

The edit form sends only the fields that changed, because the API's `PATCH`
treats absent keys as "leave alone". Two consequences:

- An **empty password box means "unchanged"**, not "clear it". Clearing a
  password has to be deliberate, so it is a CLI action
  (`user set-login-password <name>`) rather than an empty field.
- The self-demote and self-delete guards are enforced on the server, and the UI
  also disables the controls. The server guard is the real one; the disabled
  button is only a hint.

## API keys in the UI

A key's plaintext exists in exactly one response — the one that creates it. The
UI shows it in a modal with a copy button, then drops it from React state. It
cannot be shown again, so the modal says so. The label and expiry are optional
and the form sends them as explicit nulls, which the schema accepts.

Revoke is a soft flag, so a revoked key stays in the list as `revoked` and
cannot be revoked twice. The table distinguishes three states — active, expired,
revoked — because "no longer works" has different causes and an operator will
ask which.

## Conventions in the dashboard code

- TypeScript in `strict` mode. `npm run typecheck` is the gate; `vite build`
  does not typecheck, so run it explicitly.
- The API surface is declared once per resource in `src/api/` and the UI never
  calls `fetch` directly. That is what keeps every error, auth header and
  token-storage touch in one file.
- Styling is **Tailwind CSS v4**, wired in as a Vite plugin rather than PostCSS, so
  there is no `tailwind.config.js` to drift out of step with the tokens. The whole
  design system is `src/styles.css`: an `@theme` block holding the palette, the
  radii, the shadows and the four keyframe animations, a `@layer base` for bare
  element defaults, and a small `@layer components` for the patterns that repeat
  — `.btn`, `.badge`, `.card`, `.panel`, `.data-table`, `.banner`, `.menu`. A page
  uses utilities for one-off layout and those classes for anything it repeats;
  the classes exist so a button is not twenty utilities in twelve files.
- **The palette is one dark neutral ramp, one accent, and three semantic colours**
  that only mean success, attention or failure. Adding a colour per screen is what
  makes an interface look busy rather than designed.
- **Motion is restrained on purpose**: a page fades up on entry, a dialog rises,
  a drawer slides, the loading ring turns, and everything else is a 150ms
  `transition-colors` on hover. Every animation is behind
  `prefers-reduced-motion`.
- **A dialog is rendered into `document.body` through a portal, and that is
  load-bearing.** A page holds a transform while it fades up, and any element
  with a transform becomes the containing block for `position: fixed`
  descendants — so a `fixed inset-0` backdrop rendered inside the page is laid
  out against the page box instead of the viewport, lands in the wrong place, and
  can push its own buttons outside the backdrop where they cannot be clicked. For
  the same reason `--animate-fade-up` uses `backwards`, not `both`: `both` keeps
  the final keyframe applied after the animation ends, and a final
  `transform: none` still computes to an identity matrix, which is enough to
  re-create the containing block.
- Presentational pieces live in `src/components/`, one per file; pages stay
  focused on data and state. `AppShell` owns the layout and the mobile drawer's
  open state, `Sidebar` owns the navigation, and `UserMenu` owns the avatar
  dropdown — three files rather than one `Layout` with three reasons to change.
- **Every user-facing string goes through `t()` from `useI18n()`.** There are no
  inline English strings left in a page, a component or a modal, and a
  `MessageSpinner` exists so a loading label is a key rather than a string. The
  only English left on screen is deliberate and listed in `domains/i18n.md`:
  CLI commands in `<code>`, the two Telegram button names, and a product's own
  title.
- **The language is the account's, not the browser's**, and it arrives on the
  signed-in user — see `domains/i18n.md` for why, and for the `localStorage`
  fallback that covers the login screen only.
- **The language picker is on the profile page**, not in the avatar menu. It is a
  server-side setting that also decides the language of the user's notifications,
  so it belongs with the other account settings rather than in a global-looking
  menu; one place to change it, not two.
- **`session.refresh()`** exists because of that: the shell reads the language
  from the session, so a `PATCH /me/profile` that changes it has to be followed by
  a re-read, or the page switches language while the shell around it does not.
  It is separate from `invalidate()`, which signs out.
- **CSS must use logical properties** — `ms-`/`me-`, `ps-`/`pe-`, `start-`/`end-`,
  `text-start`, `border-s`/`border-e` — because `dir="rtl"` is what mirrors the
  interface for Arabic, and it only works if nothing is pinned to a side. In
  `styles.css` that means `inset-inline-end` on `.menu` and `text-align: start` on
  `.data-table th` rather than `right` and `left`.
