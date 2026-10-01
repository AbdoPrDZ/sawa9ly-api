# Authentication and Sessions

Two independent credential systems, and confusing them is the main risk here.

| | API key | Dashboard password | Sawa9ly session |
| --- | --- | --- | --- |
| Purpose | identifies a machine caller to *us* | identifies an admin to *us* | identifies us to the *site* |
| Presented as | `X-API-Key` header | `Authorization: Bearer <token>` | never leaves the server |
| Lives in | `api_keys` table | `users.password_hash` (hash) | `settings` row, per user |
| Who holds it | the caller | the person, in a browser | the server |
| Lifetime | until revoked or expired | token expires after 12h | until Laravel expires it |

An API key is not one credential but two: `api_keys.type` decides whether it opens
the HTTP API or the MCP server, and a key is accepted by exactly one of them. See
**API keys** below, and `mcp.md` for the surface on the other side.

A machine request presents an API key; that resolves a `User`; that user's stored
sawa9ly session is then used for the site. A browser presents a password, gets a
 signed token, and uses that token on `/api/auth` and `/api/admin`. **Neither
credential reaches the site and the site's cookie is never sent to a client.**

`Authorization: Bearer` is overloaded, and the two tokens have different formats,
so a value has to be tried as each before either can be ruled out. Two
dependencies read it: `get_current_user` accepts **only** an API key, and
`get_any_user` accepts either, token first.

`get_any_user` is for the resources a machine and the dashboard both need — today
`/api/v1/trackers`, `/api/v1/orders`, `/api/v1/clients`, `/api/v1/pages` and
`/api/v1/telegram`.
Widening to a token is only safe on a route that scopes by `order.user_id`,
`client.user_id` or `page.user_id` in the database; it must never be used on a
route where the credential is the only thing standing between the caller and
another user's data. `/api/v1/cart`, `/api/v1/checkout` and `/api/v1/products`
stay API-key only for that reason.

`/api/admin/orders` is the deliberate exception that proves the rule: it spans users,
so it takes a **dashboard token only** and additionally requires the `super` role
(`Dependencies.require_super`). No API key can reach it, however old.

## The signing secret lives in the database

`Token.signing_secret` falls back to a row in `app_secrets` when `DASHBOARD_SECRET`
is not set, so the key survives a restart. The cost is that **deleting the
database invalidates every dashboard session at once** — a fresh `app_secrets` means
a new key, and every outstanding token stops verifying. The symptom is that
everybody is signed out at the same moment with no error from the site. Set
`DASHBOARD_SECRET` in the environment if that matters; see `config.md`.

## API keys

- **Hashed at rest.** Only a SHA-256 hash is stored, alongside a short prefix
  that exists so a human can tell two keys apart in a listing. Plaintext is
  returned exactly once, at creation, and is never recoverable afterwards.
- **Lookup hashes the candidate** and finds the row. Do not add a plaintext
  column, a reversible encoding, or a "compare in Python" fallback.
- **Revocation and expiry are flags, not deletion.** A revoked key stays as a row
  so its history is visible; `is_valid` is the check. Deleting the row is how you
  lose the ability to audit it.
- **`touch()` records last use**, which is why an authenticated request commits.
  That is the only write an otherwise read-only request performs.
- Never log a key, include one in an error message, or echo one in a response
  after creation. `main.py login` printing a cookie is the single deliberate
  exception in the project, and it is a cookie rather than a key.

### A key opens one door, not two

`api_keys.type` is `api` or `mcp`, and it is checked in the **lookup**
(`ApiKey.find(db, token, KeyType.API)`), not afterwards. That ordering is the
whole point: a key of the wrong type must come back as *not found*, so refusing it
cannot be used to confirm that somebody else's credential exists. A post-hoc
`if key.type != ...` would answer the same 401 while quietly revealing the row
exists.

They are separate because they are handed to different things. An `api` key is
typed into a script by its owner. An `mcp` key is typed into an AI agent's client
configuration, which means it lands in transcripts, tool arguments and whatever
context the model is given, and it cannot be scoped down per-call the way a shell
variable can. One key accepted by both surfaces would put `/api/admin` behind a
token that is by construction read by a language model.

The column defaults to `api` in Python **and** as a `server_default`, so every key
that existed before the column did is an `api` key and keeps working. Adding a
column still needs the `ALTER TABLE` that `database.md` describes; `create_all`
will not do it.

Where a key is issued, all of which take the type: `POST /api/keys` (self),
`POST /api/admin/users/{id}/api-keys` (super, for another user), the dashboard's
issue form, and `apikey create --type`. `ApiKey.create` rejects an unknown type
rather than storing one nothing accepts, and the controllers turn that into a 400
because the value came off the wire.

## The third credential is a sign-in, not a key

The MCP server accepts **an OAuth sign-in** as well as an `mcp` key, and the two
are not a third entry in this table: they differ in kind. A key is looked up in a
row; a sign-in is verified from a signature.

- **A person signs in with their dashboard password.** The MCP server is its own
  OAuth authorization server — see `mcp.md` — and `User.check_password` is what
  decides. So there is no third-party identity provider and no mapping somebody
  else's subject onto a sawa9ly account: signing in *is* the lookup. The
  credential that results is as strong as the dashboard's, and reaches exactly
  what that user reaches.
- **Its tokens are signed and stateless**, in the same shape as this page's
  `Token` but with a different issuer, and that difference is load-bearing: one
  verifier must never accept the other's tokens, and a shared issuer is how that
  happens by accident.
- **They cannot be revoked individually.** An hour's life, or rotate the signing
  secret for everybody. Same trade the dashboard's twelve-hour tokens already
  make, and for the same reason — a per-token table would be a second answer to
  "who is signed in", and this project has one.
- **The user is re-read on every request**, so an account deleted mid-session
  loses access at once rather than at expiry, exactly as `get_token_user` does.
- **`tools/list` is no longer open.** With auth on the whole endpoint, anything
  that can reach the port can still read the two discovery documents — which name
  the server's endpoints — so loopback is still the right default, but for a
  smaller thing than it was.

## Per-user sessions

Each `Livewire` belongs to one user and keeps that user's session, which is why
two users never share a cart. This is the invariant the whole multi-user design
rests on.

- Cookies are scoped to the `sawa9ly.app` **apex** domain deliberately. A
  domain-less cookie is stored twice by the jar and Laravel then reads the stale
  copy, producing intermittent "logged out" behaviour that looks random.
- Requests go to the `sawa9ly.app` apex. `www.sawa9ly.com` 301-redirects, and a
  POST is silently downgraded to a GET across that redirect, so a form post there
  arrives empty and fails in a way that looks like bad credentials.
- A session is validated by requesting a page that requires auth and checking
  whether it bounced to `/login`. Do not add a lighter-weight check: a cached
  page, a HEAD request, or a status code on its own will disagree with what
  Laravel actually does.
- Validity is re-checked mid-run, and a request that bounced is replayed after a
  re-login. Callers should not have to handle expiry.

## Dashboard passwords and tokens

The admin dashboard is the only thing that uses this mechanism.

- **Passwords are hashed with scrypt** (`src/utils/passwords.py`), with a random
  salt per user and a constant-time comparison. Scrypt is deliberately slower
  than a plain digest, because the threat is an offline attack on a leaked row.
  A malformed or truncated hash returns False rather than raising, so a corrupted
  row denies access instead of producing a 500.
- **`password_hash` is optional and independent of `sawa9ly_password`.** A user
  can have no dashboard password at all, in which case it cannot sign in whatever
  its role. A user with no sawa9ly credentials can still sign in to the dashboard.
  Keep them separate; conflating them reuses a site password for our own login.
- **A token is signed, not looked up** (`src/utils/tokens.py`): an HMAC over a
  base64 payload, expiring after 12 hours. There is no token table, so there is
  nothing to revoke individually — a token dies with its expiry, and a password
  change is what forces everyone out early.
- **The signing key comes from `DASHBOARD_SECRET` or is generated once** and
  stored in `app_secrets`. The stored fallback exists so the key survives a
  restart; generating a fresh one per process would silently sign everybody out
  on every deploy.
- **A token's payload is never trusted on its own.** The user is re-read from the
  database on every request, so deleting or demoting someone takes effect
  immediately instead of at token expiry. Anything that reads `role` from a token
  payload is a bug.
- **401 means "not signed in", 403 means "signed in but not an admin".** Keeping
  them apart is what lets the dashboard show the right message.
- **The API keys are still how machines authenticate.** The dashboard does not
  use an admin token on the product routes. It *does* manage keys, but through
  the caller's own `/api/keys` for anybody and the super-only admin route for
  somebody else — see "A key is the caller's own credential" below.
- The first admin is created from the CLI, not through the API, because the admin
  routes need an admin to exist first:
  `user add <name> --login-password <pw>` then `user set-role <name> admin`.
  `user add` refuses to create a passwordless admin, since one could not sign in.

## Self-lockout guards

Two rules in the admin routes exist because violating them leaves nobody able to
fix it without the CLI:

- An admin cannot remove their own admin role.
- An admin cannot delete their own account.

A third is structural: the dashboard **cannot create a `super`, and cannot change
or delete one**. The role is not offered in any dropdown, and the API refuses it
with a 403 even for a hand-crafted request. Nobody working in the UI can promote,
demote or delete the account above them, so a super is only manageable through
`SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` or the CLI.

## Roles and what each may do

| role | may do |
| --- | --- |
| `super` | edit and delete any user, see who has set up their account, and issue a key in anybody's name |
| `admin` | add users, list users, see and revoke **every** user's keys, and manage **their own** profile and keys |
| `user` | manage their own profile and their own API keys only |

An administrator's power is deliberately narrow: create an account and set the
dashboard password to reach it with. That is all.

## A key is the caller's own credential

Issuing and revoking keys is split across two controllers, and the split *is* the
permission model:

| Route | Gate | Reaches |
| --- | --- | --- |
| `GET/POST /api/keys` | `require_user` | the caller's own keys, and no user in the path or body at all |
| `DELETE /api/keys/{id}` | `require_user` | the caller's own key; anyone else's is a **404**, not a 403 |
| `GET /api/admin/api-keys` | `require_admin` | every key for every user |
| `DELETE /api/admin/api-keys/{id}` | `require_admin` | any key |
| `POST /api/admin/users/{id}/api-keys` | `require_super` | a key in another user's name |

So **every signed-in user can mint and drop their own keys, and only a `super`
can mint one in somebody else's name.** The rule is enforced server-side by the
two different gates, not by the dashboard hiding the picker — a hand-crafted
request to `/api/admin/users/{id}/api-keys` is a 403 for an admin exactly as it is
for a plain user.

`POST /admin/users/{id}/api-keys` was `require_admin` before this and is
`require_super` now. That tightening is the point, not a side effect: handing
somebody a credential in their name is a root-level act, and it was reachable by
any admin.

**404 rather than 403 on somebody else's key id**, so the self-service revoke
cannot be used to find out which keys other people hold.

`/api/keys` has no user parameter anywhere, which is deliberate: there is nothing
to point at another account. An account with **no dashboard password** cannot use
it, because it cannot sign in to reach it — those are the API-only users, and a
super issues their key from the admin route. That is the only reason the admin
issue route needs to exist at all.

`ApiKeysController._out` is shared: both controllers return the same
`AdminApiKeyOut` shape so the dashboard renders one table for both views, rather
than the same component handling two row types.

**No role may set another user's sawa9ly credentials.** Not a super, not through
the API, not through the dashboard. The fields are not on `AdminUserIn` at all, so
there is nothing to authorise — `Accounts.may_set_site_credentials` was removed
rather than left as a door nothing opens. The user sets their own from
`/api/auth/me/profile`, so the credential always comes from the person who owns
it, and an admin who could type it in could also act as that user on the site.

What an admin *can* see is the **fact** that a user is set up —
`has_sawa9ly_credentials`, and `telegram_chat_id` — not the value. That is enough
to answer "why is this account not syncing?" without the admin holding somebody
else's address or chat.

The whole matrix is in `src/services/accounts.py` as `may_*` methods returning
`(allowed, reason)`. Two reasons that pattern exists:

- the route handlers stay free of role comparisons, so the matrix is readable in
  one place and cannot drift between endpoints;
- the `reason` string is what the API returns, and every one of them says what to
  do instead rather than just refusing.

Self-service is separate from administration on purpose: `/api/auth/me/profile` is
open to any signed-in user, and `/api/admin/users/{id}` is super-only. A user
changing their own password never needs an administrator, and an administrator
has no business changing it for them.

The CLI's `user add --email --password` still exists, and is the one remaining way
credentials are set by anyone but their owner. It is the operator's own bootstrap
path on a machine where the user cannot yet sign in, so it was left alone when the
dashboard path was removed. Say so if that is wrong.

## Sawa9ly credentials

Each user stores its own sawa9ly `email` and `password` in `users`, so a session
can be re-established without knowing which account is behind it.

**There is no environment fallback, for anyone.** This is the single most
important rule in this file: it is what stops a user created for API access from
silently borrowing the operator's account, and with it the operator's cart and
order history. A user with no credentials simply cannot sign in, and
`User.credentials` says which command records them.

Consequences worth respecting:

- A user without credentials cannot log in, and the failure must name the user,
  not leak anything else.
- Credentials are a secret. They live in a gitignored database, and the
  `credentials()` accessor exists so no caller reaches around it into the columns.
- `--user` is optional and falls back to the `super` account, read from the
  database rather than the environment. An installation with several supers is
  refused rather than guessed at, because silently acting for the wrong account is
  the failure this prevents. See `config.md`.

## Adding to this area

- A new auth mechanism means a new credential type in its own table with the same
  discipline: hash at rest, return once, never log.
- Never key anything off a user id that came from the request. The authenticated
  user is the only user.
- A new **machine** credential on an existing table is a `KeyType` value, not a
  new table. Check the type in the lookup, so a key of the wrong type is
  indistinguishable from one that does not exist.
- A new front end needs its own credential *unless* it is a second caller of the
  same operations by the same people. The MCP server took a new type because it
  hands its key to a language model; a read-only status page would not need one.
