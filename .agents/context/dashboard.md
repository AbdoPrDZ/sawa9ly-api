# Admin Dashboard

A React single-page app for admins: manage users and API keys. It is the only
front end that talks to `/auth` and `/admin`; everything else in the API is
designed for machine callers.

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
    trackers.ts            listTrackers, watch, unwatch
    users.ts               listUsers, createUser, updateUser, deleteUser
    keys.ts                listKeys, createKey, revokeKey
  session/
    context.ts             the Session type and React context
    SessionProvider.tsx    holds the user, restores and signs in
    useSession.ts          the hook pages use
  components/              Banner, Field, Modal, RoleBadge, KeyState, Spinner,
                           TopBar, WatchButton, FetchProduct
  features/
    users/                 CreateUserModal, EditUserModal, DeleteUserModal
    keys/                  IssueKeyModal, RevokeKeyModal, RevealKeyModal
  pages/                   Login, Users, ApiKeys, Profile, Products,
                           ProductDetail
```

`api/` is split by resource and `features/` by the flow it belongs to, so a new
endpoint or a new modal is a new file rather than an addition to a shared one.
The UI never calls `fetch`; it goes through `api/`, which is the only place that
attaches a token or turns an error into a message.

## What is served

```text
public/                     source; never served
  src/                      app code
  dist/                     build output; the only part served
  vite.config.ts            build config and the dev proxy
```

The API mounts **`public/dist` only**. The source, `node_modules` and
`package.json` are never exposed. Do not change the mount to `public/`.

Consequences worth remembering:

- The build directory is `assets`, not Vite's default `static`, because the
  server mounts `/assets`. Renaming it in `vite.config.ts` breaks asset loading.
- `dist/` is a build artifact and is gitignored. It is rebuilt, not committed.
- Every unknown non-API path returns `index.html` so the client-side router can
  navigate, but a path that names a real file is served as that file, so a
  missing asset is a 404 rather than HTML with a 200.
- A resolved path is checked to be inside `dist/` before being served, which is
  what stops `../` from walking out of the build.

## Building and running

```bash
cd public
npm install
npm run dev      # Vite on :5173, proxying /v1 /auth /admin /health /me to :8000
npm run build    # writes dist/
npm run typecheck
```

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

The bundle contains no API host. It calls `/auth/login`, not
`http://127.0.0.1:8000/auth/login`, because the dashboard is served from the
same origin as the API. That is what removes the need for CORS configuration
and for any environment-specific build variable. **Do not introduce
`import.meta.env.VITE_API_URL` or a base URL** unless the dashboard is genuinely
served from a different origin than the API.

The version prefix is applied in exactly one place, `urlFor` in
`public/src/api/client.ts`, called from `request()`. The per-resource modules
pass bare paths (`request('/auth/me')`) and stay prefix-agnostic, so a `/v2` is
that one constant rather than an edit to every api module.

`UNVERSIONED_PREFIXES` in the same file is the deliberate exception: the
dashboard's own `/auth` and `/admin` are mounted unversioned on the server,
because this app is their only caller. **The server is the authority** — the
list in `client.ts` is the client half of the same fact, and the two must agree.
Adding a new dashboard-only endpoint means adding it to both.

The dev proxy exists only to reproduce same-origin behaviour locally. Its list
in `vite.config.ts` is `v1`, `auth`, `admin`, `health` and `me`. Versioning also
retired the old route collision: the API's scrape routes are `/v1/products/{id}`
and the dashboard's own page is `/products`, so no proxy prefix can serve both.

## Pages and who sees them

| Route | Page | Who |
| --- | --- | --- |
| `/profile` | `ProfilePage` | every signed-in user |
| `/products` | `Products` | administrators |
| `/products/:productId` | `ProductDetail` | administrators |
| `/users` | `Users` | administrators |
| `/keys` | `ApiKeys` | administrators |

**A plain user is not locked out.** They get the same shell with only their
profile, because managing their own account is not something an administrator
should have to unlock. `TopBar` omits the admin links for them, and the admin
routes redirect to `/profile` rather than letting a request fail with a 403.

The profile page is the self-service surface: the dashboard password, the
sawa9ly email and password, and a **Log in to sawa9ly** button that creates or
refreshes that account's site session. The button is disabled until the account
has both site credentials, and the page shows whether a stored session exists.

## Products

`Products` lists the saved catalogue and is the landing page for an admin. It has
one control that reaches the site: **fetch a product by its id**, which scrapes
the page and stores the result. That is a deliberate form, not a button on every
row, because it is the only dashboard action that makes the server talk to
sawa9ly.

`ProductDetail` shows one product with an image gallery, and a `WatchButton` that
starts or stops tracking it. It handles the "not saved yet" case by offering the
same fetch, because a 404 on a product page is otherwise a dead end.

Both pages read the watch state from `/v1/trackers` once and match by
`product_id`, rather than asking per row. `WatchButton` re-reads the server's
answer after a failed toggle instead of keeping whatever the failed attempt
intended — the server is the truth about what is watched.

The catalogue routes take **no authentication at all**, including the POST that
scrapes. That predates the dashboard and is left alone deliberately, but the
dashboard makes it easier to reach, so it is worth an access rule before this is
exposed to anyone.

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

The dashboard signs in with `POST /auth/login` and stores the returned token in
`localStorage`. That token is not an API key and is not interchangeable with one;
see `domains/authentication.md` for how the two differ.

Two rules the code follows, both of which are easy to break:

- **A stored token is re-checked against the server before anything is
  rendered.** A token in `localStorage` proves nothing — it may have expired, or
  the user may have been demoted or deleted since. The app shows a spinner until
  `/auth/me` answers, which is also why a reload does not flash the login screen
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
- The API surface is declared once in `src/api.ts` and the UI never calls
  `fetch` directly. That is what keeps every error, auth header and
  token-storage touch in one file.
- Styling is plain CSS in `src/styles.css` with custom properties for the
  palette. There is no CSS framework — a dashboard does not justify one, and it
  keeps the bundle at a size that is not worth optimising.
- Presentational pieces live in `src/ui.tsx`; pages stay focused on data and
  state.
