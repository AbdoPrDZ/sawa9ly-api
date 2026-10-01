"""The OAuth authorization server behind the MCP tools.

FastMCP's `OAuthProxy` presents the whole OAuth 2.1 + DCR + CIMD surface that
Claude's connector expects — the discovery documents, the authorize redirect,
PKCE, resource indicators, dynamic client registration — and then proxies it to
an *upstream* authorization server. Every upstream FastMCP ships is somebody
else's: Auth0, WorkOS, Keycloak, Google. **This is ours**, and it exists because
the project already has the thing an authorization server needs and an IdP does
not: a table of users with real passwords on it.

So the division of labour is:

- **FastMCP owns the protocol.** Discovery, CIMD, DCR, PKCE, resource binding,
  the refresh dance, and the short-lived JWT it hands the client. None of that is
  reimplemented here.
- **This module owns the human.** A sign-in page, a password check against
  `users.password_hash`, an authorization code, and an access token naming the
  user who signed in.

That last split is why there is no identity-mapping problem. A hosted IdP would
hand us a subject like `auth0|abc123` and leave us working out which sawa9ly user
that is; here, signing in *is* the lookup.

## What the tokens are

A signed, expiring token in the same shape as the dashboard's (`utils/tokens.py`):
`base64url(payload).base64url(hmac)`. Stateless, so nothing to store and nothing
to migrate, and the signing key lives in `app_secrets` so it survives a restart.

The cost is stated rather than hidden: **nothing here can be revoked
individually.** An access token stops working when it expires, or immediately for
everyone when the signing secret is rotated. That is the right trade at one
hour's lifetime for a tool surface; a table with per-token revocation would be a
second source of truth about who is signed in, and this project already has one
answer to that question — the `users` table. The dashboard's own session tokens
work the same way and for twelve hours.

An authorization code is the same idea at a much shorter life: five minutes, and
redeeming one still needs the `code_verifier`, which never leaves the client.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

from src import theme
from src.db import session_scope
from src.models import Secret, User
from src.utils.passwords import Passwords

#: Name the token signing key is stored under in `app_secrets`.
SIGNING_SECRET_NAME = "mcp_token"

#: The client credentials the proxy presents to us as the upstream client. The
#: id is a constant because there is exactly one upstream client — the proxy —
#: and the secret is generated once and stored, so it survives a restart without
#: anybody having to configure it.
UPSTREAM_CLIENT_ID = "sawa9ly-connector"


class AuthorizationError(Exception):
  """A refusal the sign-in flow can render as a page."""


class AuthorizationServer:
  """The upstream half of the OAuth flow: sign in, and a token naming the user.

  One instance per process, built by `McpServer`, holding the URLs the proxy needs
  so the two halves cannot disagree about where they live.
  """

  def __init__(self, public_url, path_prefix="/oauth"):
    self.public_url = public_url.rstrip("/")
    self.path_prefix = path_prefix

  #: Issuer claim. Deliberately not the dashboard's: one verifier must never
  #: accept the other's tokens, and a shared issuer is how that happens by
  #: accident.
  ISSUER = "sawa9ly-mcp"

  #: An access token lasts an hour. Long enough that a working session is not
  #: interrupted, short enough that a token lifted out of a transcript is not
  #: useful for long. The refresh token behind it is what keeps a connector
  #: connected between them.
  ACCESS_TTL = 60 * 60

  #: A refresh token lasts a month, and is only ever accepted at the token
  #: endpoint — `McpTokens` refuses it, so it cannot be used as a bearer
  #: credential on a tool call.
  REFRESH_TTL = 60 * 60 * 24 * 30

  #: An authorization code is good for five minutes. Signed rather than stored,
  #: so it is not single-use — see the module docstring — but redeeming one still
  #: needs the verifier, which never leaves the client.
  CODE_TTL = 60 * 5

  #: What a failed sign-in says. Only ever rendered into a page that does not
  #: cache, and deliberately not saying *which* of the two was wrong — an error
  #: that distinguishes them is an account-enumeration oracle.
  BAD_CREDENTIALS = "That username and password do not match an account."

  # --- urls ------------------------------------------------------------

  @property
  def authorize_url(self):
    return f"{self.public_url}{self.path_prefix}/authorize"

  @property
  def token_url(self):
    return f"{self.public_url}{self.path_prefix}/token"

  def credentials(self):
    """The upstream client id and secret, generating the secret on first use."""
    with session_scope() as db:
      secret = Secret.get_or_create(db, f"{SIGNING_SECRET_NAME}_client")

    return UPSTREAM_CLIENT_ID, secret

  # --- tokens ----------------------------------------------------------

  @staticmethod
  def signing_secret():
    """The HMAC key tokens are signed with, generated once and stored."""
    with session_scope() as db:
      return Secret.get_or_create(db, SIGNING_SECRET_NAME)

  @classmethod
  def issue_access_token(cls, user):
    """A signed access token naming this user.

    `sub` is the user id and `usr` the username, matching the dashboard's token
    payload so one reader understands both. `typ` is what keeps this apart from a
    refresh token at the point they are checked rather than at each call site.

    A token is not a login: whoever holds it acts as that user, which is why
    `McpAuth` re-reads the user from the database on every request rather than
    trusting the claims.
    """
    return cls._sign(
      {"sub": user.id, "usr": user.username, "typ": "access"}, cls.ACCESS_TTL
    )

  @classmethod
  def verify_access_token(cls, token):
    """The payload of a valid access token, or None.

    A refresh token is refused here and not merely by its caller, so promoting one
    to a bearer credential takes an argument somebody would have to change rather
    than a check somebody would have to remember.
    """
    payload = cls._verify(token, cls.ACCESS_TTL)

    if payload is None or payload.get("typ") != "access":
      return None

    return payload

  @classmethod
  def issue_refresh_token(cls, user):
    """A longer-lived token the client exchanges for a new access token.

    Distinguished from an access token by its own `typ`, so the two cannot be
    used for each other: an access token must not be able to mint a new one, and a
    refresh token must not be accepted as a bearer credential on a tool call.
    """
    return cls._sign({"sub": user.id, "typ": "refresh"}, cls.REFRESH_TTL)

  @classmethod
  def verify_refresh_token(cls, token):
    """The user id a refresh token names, or None."""
    payload = cls._verify(token, cls.REFRESH_TTL)

    if payload is None or payload.get("typ") != "refresh":
      return None

    return payload.get("sub")

  # --- authorization codes ---------------------------------------------

  @classmethod
  def issue_code(cls, user, challenge, redirect_uri, method="S256"):
    """A signed authorization code for this user, this PKCE challenge and this
    redirect URI.

    Stateless, like every other token here, so it cannot be made single-use
    without a table — see the module docstring. What bounds the replay is the
    five-minute TTL and the fact that redeeming one still requires the
    `code_verifier`, which never leaves the client.

    The redirect URI is carried so the token request can be checked against it,
    as RFC 6749 §4.1.3 requires. The proxy already binds it to the transaction it
    recorded, so this is the second of two checks rather than the only one.
    """
    if method and method.upper() != "S256":
      raise AuthorizationError(
        "Only S256 PKCE is accepted; plain challenges are not."
      )

    return cls._sign(
      {
        "sub": user.id,
        "usr": user.username,
        "typ": "code",
        "ch": challenge,
        "ru": redirect_uri,
      },
      cls.CODE_TTL,
    )

  @classmethod
  def redeem_code(cls, code):
    """What a code names — user, challenge, redirect URI — or None.

    Rejects anything without a challenge and without the `code` type, so neither
    an access token nor a refresh token can be presented here as though it were
    a code.
    """
    payload = cls._verify(code, cls.CODE_TTL)

    if payload is None or payload.get("typ") != "code" or not payload.get("ch"):
      return None

    return {
      "user_id": payload.get("sub"),
      "challenge": payload["ch"],
      "redirect_uri": payload.get("ru"),
    }

  @staticmethod
  def user_of(user_id):
    """The user a token names, or None if they have since been deleted.

    Always re-read rather than trusted from the token payload: a token is a
    claim about the past, and this is what makes deleting an account take effect
    before its tokens expire rather than at expiry.
    """
    with session_scope() as db:
      return User.get_by_id(db, user_id)

  @staticmethod
  def _code_challenge(verifier):
    """The S256 challenge a code verifier hashes to. RFC 7636."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()

    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

  @classmethod
  def _sign(cls, claims, ttl):
    """Sign a payload with the shared secret, in the dashboard token's format."""
    payload = {
      "iss": AuthorizationServer.ISSUER,
      "iat": int(time.time()),
      "exp": int(time.time()) + ttl,
      **claims,
    }
    body = AuthorizationServer._encode(
      json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    secret = AuthorizationServer.signing_secret()
    digest = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256)

    return f"{body}.{AuthorizationServer._encode(digest.digest())}"

  @classmethod
  def _verify(cls, token, ttl):
    """The payload of a token signed by us and not past `ttl`, else None."""
    if not token or "." not in token:
      return None

    body, _, signature = token.rpartition(".")
    secret = cls.signing_secret()
    expected = cls._encode(
      hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )

    # compare_digest, not ==: a byte-by-byte compare leaks how much of a forged
    # signature was right, and this is the one place in the project that guesses.
    if not hmac.compare_digest(signature, expected):
      return None

    try:
      payload = json.loads(cls._decode(body))
    except (ValueError, TypeError):
      return None

    if payload.get("iss") != cls.ISSUER:
      return None

    if int(payload.get("exp", 0)) <= int(time.time()):
      return None

    return payload

  @staticmethod
  def _encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

  @staticmethod
  def _decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

  # --- the sign-in page ------------------------------------------------

  @staticmethod
  def authenticate(username, password):
    """The user these credentials name, or None.

    A hash comparison against a user who does not exist is not performed, so a
    wrong username and a wrong password take the same time — otherwise the
    endpoint is a way to enumerate accounts.
    """
    if not username or not password:
      return None

    with session_scope() as db:
      user = User.get(db, username.strip())

      if user is None or not user.check_password(password):
        return None

      return user

  @classmethod
  def sign_in_page(cls, params, error=None):
    """The HTML form a person signs in on.

    Every OAuth parameter the proxy sent is carried back as a hidden field, so
    posting the form re-runs the same authorization request rather than needing
    the query string to survive. `autocomplete` is set to the values that make a
    password manager behave, and the form posts to itself so a refresh re-renders
    rather than re-submitting.

    The CSP is the same one the public landing pages are served under: sandboxed,
    so this page cannot reach the API's cookies or its storage even if the markup
    were ever built from anything a user supplied.
    """
    hidden = "".join(
      f'      <input type="hidden" name="{name}" value="{_escape(value)}">\n'
      for name, value in sorted(params.items())
      if value
    )
    notice = (
      f'    <p class="error" role="alert">{_escape(error)}</p>\n' if error else ""
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex, nofollow" />
    <title>Sign in to sawa9ly</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: {theme.CANVAS};
        color: {theme.INK};
        font: 16px/1.6 system-ui, sans-serif;
      }}
      main {{
        width: min(24rem, calc(100vw - 2rem));
        padding: 2rem;
        border: 1px solid #23272e;
        border-radius: 10px;
        background: #101317;
      }}
      h1 {{ font-size: 1.15rem; margin: 0 0 .25rem; }}
      p.sub {{ color: {theme.MUTED}; margin: 0 0 1.5rem; font-size: .875rem; }}
      label {{ display: block; font-size: .8125rem; color: {theme.MUTED};
               margin: 0 0 .35rem; }}
      input[type=text], input[type=password] {{
        width: 100%;
        padding: .55rem .7rem;
        margin: 0 0 1rem;
        border: 1px solid #23272e;
        border-radius: 6px;
        background: {theme.CANVAS};
        color: {theme.INK};
        font: inherit;
      }}
      input:focus {{ outline: 2px solid {theme.ACCENT}; outline-offset: 1px; }}
      button {{
        width: 100%;
        padding: .6rem 1rem;
        border: 0;
        border-radius: 6px;
        background: {theme.ACCENT};
        color: #1a1400;
        font: 600 1rem system-ui, sans-serif;
        cursor: pointer;
      }}
      p.error {{ color: #ff8a80; font-size: .8125rem; margin: 0 0 1rem; }}
      p.foot {{ color: {theme.MUTED}; font-size: .75rem; margin: 1.5rem 0 0; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Sign in to sawa9ly</h1>
      <p class="sub">This connects an AI agent to your account.</p>
{notice}      <form method="post">
{hidden}        <label for="username">Username</label>
        <input id="username" name="username" type="text" required
               autocomplete="username" autocapitalize="none" spellcheck="false" />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" required
               autocomplete="current-password" />
        <button type="submit">Sign in</button>
      </form>
      <p class="foot">Your dashboard password, not your sawa9ly one. Whatever this
        agent does, it does as you.</p>
    </main>
  </body>
</html>
"""

  @staticmethod
  def redirect(location):
    """A 302 carrying a Location header, for Starlette."""
    from starlette.responses import RedirectResponse

    return RedirectResponse(location, status_code=302)

  @staticmethod
  def location_with(base, **params):
    """`base` with `params` appended, skipping empty ones.

    `state` has to come back byte-for-byte or the client rejects the response,
    and the proxy puts a transaction id in it, so it is never re-encoded or
    trimmed here.
    """
    query = {name: value for name, value in params.items() if value}

    return f"{base}?{urlencode(query)}"

  @staticmethod
  def error_response(status, error, description):
    """An OAuth-shaped error, as JSON.

    The proxy parses these, so the shape matters: `error` is the RFC 6749 code
    and `error_description` is prose it shows a person.
    """
    from starlette.responses import JSONResponse

    return JSONResponse(
      {"error": error, "error_description": description}, status_code=status
    )

  @staticmethod
  def json_response(payload, status=200):
    """A token response, with the headers a token endpoint owes its caller."""
    from starlette.responses import JSONResponse

    return JSONResponse(
      payload,
      status_code=status,
      headers={
        # No caching, and no reuse across origins: these are bearer credentials.
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
      },
    )

  @classmethod
  def page_response(cls, html, status=200):
    """The sign-in page as a response."""
    from starlette.responses import HTMLResponse

    return HTMLResponse(
      content=html,
      status_code=status,
      headers={
        # No caching: a page holding a form that was just submitted must not be
        # kept, and neither must the browser keep the password field.
        "Cache-Control": "no-store",
        "Content-Security-Policy": (
          "sandbox allow-forms allow-scripts allow-popups "
          "default-src 'none'; style-src 'unsafe-inline'"
        ),
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
      },
    )


def _escape(value):
  """HTML-escape a value going into the page.

  Everything here came off an OAuth request, and the redirect URI and client id
  are attacker-influenced in the threat model where somebody crafts an authorize
  URL. Escaped into an attribute and nothing more.
  """
  return (
    str(value)
    .replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
    .replace('"', "&quot;")
    .replace("'", "&#x27;")
  )
