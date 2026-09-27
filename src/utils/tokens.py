"""Signed, expiring tokens for the admin dashboard.

A token is what a signed-in browser sends back instead of an API key. It is
deliberately not an API key: it expires, it names a role, and it is signed with
the app's own secret rather than looked up in a table.

The format is `base64url(payload).base64url(hmac)` — JWT-shaped, without the
nested header and without a dependency. The signature is what makes it
unforgeable; the payload is readable but is never trusted on its own, which is
why the caller always re-reads the user from the database afterwards.
"""

import base64
import hashlib
import hmac
import json
import time

from src.config import Config
from src.models import Secret

# Name under which the generated secret is stored when the environment does not
# supply one. The environment variable is Config.DASHBOARD_SECRET_VAR.
SIGNING_SECRET_NAME = "dashboard_token"


class Token:
  """Issues and verifies dashboard session tokens."""

  # Long enough for a working day, short enough that a stolen browser session is
  # not useful for ever.
  TTL = 60 * 60 * 12
  ISSUER = "sawa9ly-dashboard"

  @staticmethod
  def signing_secret(db):
    """The HMAC key, from the environment or generated once and stored.

    The database fallback exists so a local run needs no configuration and,
    crucially, so the key survives a restart instead of logging every admin out.
    """
    configured = Config.dashboard_secret()

    if configured:
      return configured

    return Secret.get_or_create(db, SIGNING_SECRET_NAME)

  @staticmethod
  def issue(user, secret, ttl=TTL):
    """Return a token for this user, valid for `ttl` seconds."""
    payload = {
      "iss": Token.ISSUER,
      "sub": user.id,
      "usr": user.username,
      "role": user.role,
      "iat": int(time.time()),
      "exp": int(time.time()) + ttl,
    }
    body = Token._encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    return f"{body}.{Token._sign(body, secret)}"

  @staticmethod
  def verify(token, secret):
    """The token's payload, or None if it is not valid.

    Rejects a bad signature, the wrong issuer and an expired token. It does
    *not* check that the user still exists or is still an admin — a token whose
    user has since been deleted or demoted must lose access immediately rather
    than at expiry, so the caller resolves the user and re-reads its role.
    """
    if not token or "." not in token:
      return None

    body, _, signature = token.rpartition(".")
    expected = Token._sign(body, secret)

    if not hmac.compare_digest(signature, expected):
      return None

    try:
      payload = json.loads(Token._decode(body))
    except (ValueError, TypeError):
      return None

    if payload.get("iss") != Token.ISSUER:
      return None

    if int(payload.get("exp", 0)) <= int(time.time()):
      return None

    return payload

  # --- plumbing -------------------------------------------------------

  @staticmethod
  def _sign(body, secret):
    digest = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256)

    return Token._encode(digest.digest())

  @staticmethod
  def _encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

  @staticmethod
  def _decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
