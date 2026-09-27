# Authentication and Sessions

Two independent credential systems, and confusing them is the main risk here.

| | API key | Dashboard password | Sawa9ly session |
| --- | --- | --- | --- |
| Purpose | identifies a machine caller to *us* | identifies an admin to *us* | identifies us to the *site* |
| Presented as | `X-API-Key` header | `Authorization: Bearer <token>` | never leaves the server |
| Lives in | `api_keys` table | `users.password_hash` (hash) | `settings` row, per user |
| Who holds it | the caller | the person, in a browser | the server |
| Lifetime | until revoked or expired | token expires after 12h | until Laravel expires it |

A machine request presents an API key; that resolves a `User`; that user's stored
sawa9ly session is then used for the site. A browser presents a password, gets a
signed token, and uses that token on `/auth` and `/admin`. **Neither credential
reaches the site and the site's cookie is never sent to a client.**

`Authorization: Bearer` is overloaded: an API key on the `/cart` and `/orders`
routes, a dashboard token on `/auth` and `/admin`. They are separate dependencies
with separate token formats, so nothing is accepted by both.

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
  create keys for itself and an admin token does not work on the product routes.
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
| `super` | everything in the dashboard, including editing and deleting any user and setting their sawa9ly credentials |
| `admin` | add users, list users, manage API keys, and manage **their own** profile. Nothing else |
| `user` | manage their own profile only |

An administrator's power is deliberately narrow. They can create an account, and
that account starts with **no** site credentials — setting another user's
sawa9ly email or password is super-only, and a non-super is refused with a 403.
The user then sets their own from the profile page, so the credential always
comes from the person who owns it.

The whole matrix is in `src/services/accounts.py` as `may_*` methods returning
`(allowed, reason)`. Two reasons that pattern exists:

- the route handlers stay free of role comparisons, so the matrix is readable in
  one place and cannot drift between endpoints;
- the `reason` string is what the API returns, and every one of them says what to
  do instead rather than just refusing.

Self-service is separate from administration on purpose: `/auth/me/profile` is
open to any signed-in user, and `/admin/users/{id}` is super-only. A user
changing their own password never needs an administrator, and an administrator
has no business changing it for them.

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
- There is no default user, so `--user` is required on every command that acts
  for an account. See `config.md`.

## Adding to this area

- A new auth mechanism means a new credential type in its own table with the same
  discipline: hash at rest, return once, never log.
- Never key anything off a user id that came from the request. The authenticated
  user is the only user.
