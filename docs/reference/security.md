# Security

Three things hold secrets. Treat all of them as passwords.

| What | Contains | If leaked |
| --- | --- | --- |
| `.env` | your account email and password, in plain text | the account can be logged into, and the password tried elsewhere |
| `database/sawa9ly.db` | session cookies and the sawa9ly password of every user | the account can be used until the session expires, with **no password needed** |
| an API key | one user's full access to the API, or to the MCP server | that user can place orders, and read their saved data |
| an MCP sign-in | the same, obtained by typing a dashboard password into the connector's sign-in page | that user can place orders; the token is held by the client |

The session cookie is `HttpOnly` and `Secure`, so scripts running on the site
cannot read it — but it is a bearer credential: whoever holds the database can
be logged in as you.

## Passwords and keys are hashed, and shown once

An **API key** is stored as a SHA-256 hash. The plaintext is printed only in the
response that creates it, so it cannot be recovered later — if you lose it,
create another and revoke the lost one.

A key is also one of two kinds, and that is a security boundary rather than a
label. `api` is accepted by `/api`; `mcp` is accepted by the MCP server, and
**neither accepts the other's key**. They are separate because an `mcp` key is
typed into an AI agent's client configuration, which means it lands in
transcripts, tool arguments and whatever context window the model is given, and it
cannot be scoped down per-call the way a shell variable can. One key accepted by
both surfaces would put `/api/admin` behind a token that is by construction read by
a language model. See [../guides/mcp.md](../guides/mcp.md).

What that key can still reach is the same user's own data: two clients never share
a cart, and no tool reaches another user's orders, recipients or pages.

## Signing in to the MCP server

A connector can sign in instead of holding a key, and the flow is this project's
own — there is no third-party identity provider. A browser lands on
`/oauth/authorize`, types the **dashboard** username and password, and gets a
signed access token.

- **The password is never stored or logged for this.** It goes to
  `User.check_password`, exactly as it does on the dashboard's own sign-in, and
  the response is `no-store` with a `Content-Security-Policy: sandbox`.
- **A wrong password says nothing about which half was wrong**, so the endpoint is
  not a way to enumerate accounts.
- **The token is signed, not stored.** Access tokens last an hour and cannot be
  revoked individually — only by rotating the `mcp_token` row in `app_secrets`,
  which signs everybody out at once. Same trade as the dashboard's session tokens.
- **An account deleted mid-flow loses access immediately**, not at token expiry:
  the user is re-read from the database on every request.

A **dashboard password** is stored as a scrypt hash with a per-user salt, and is
verified in constant time. It is unrelated to the sawa9ly password: one signs in
to the dashboard, the other signs in to the site.

A **dashboard token** is signed, not stored, and expires after 12 hours. There is
no token table, so a token cannot be revoked individually — changing the password
is what invalidates outstanding tokens early.

Nothing logs a credential. The only command that prints one is
`python main.py login`, which prints a cookie.

## Keep them out of git

All of them are in `.gitignore`. Confirm the rules actually apply:

```bash
git check-ignore -v .env database/sawa9ly.db
```

If any was already committed before the ignore rule existed, ignoring is not
enough — the contents stay in history. Untrack it:

```bash
git rm --cached .env database/sawa9ly.db
```

Never bypass with `git add -f`, and do not assume a `.gitignore` protects a file
that was added earlier. If a secret ever did reach a remote, rotate it (below);
rewriting history is not a substitute.

## Restrict file permissions

Only your own user account needs to read these files.

```powershell
# Windows
icacls .env                 /inheritance:r /grant:r "$env:USERNAME:(F)"
icacls database\sawa9ly.db  /inheritance:r /grant:r "$env:USERNAME:(F)"
```

```bash
# Linux / macOS
chmod 600 .env database/sawa9ly.db
```

## Do not leak them through output

`python main.py login` prints the cookie string to stdout, so it lands in
terminal scrollback and in anything you redirect that output to. Do not pipe it
into a shared file or a CI log. When reporting a problem, paste the error text —
never the contents of `.env` or the database, and not screenshots of them either.

## Prefer environment variables on servers

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

## Rotating if a secret is exposed

1. **Change the account password on the site.** This is the only step that
   actually protects the account; everything else is cleanup.
2. Revoke the API key: `python main.py apikey revoke <id>`. This takes effect
   immediately, even though a leaked copy of the key still works until revoked.
3. Delete the database to drop the stored session: `Remove-Item
database\sawa9ly.db`. It is rebuilt from the site on the next run.

Deleting the database only logs out *this* installation. It does not invalidate
a copy someone already took, which is why step 1 comes first.

## Sessions expire

The stored session is time-limited, and the app logs in again automatically when
it goes. That is convenience, not security: it just means a stolen session is
only useful for as long as that session lives.
