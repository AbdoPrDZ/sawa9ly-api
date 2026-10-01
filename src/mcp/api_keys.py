"""MCP API keys, as an OAuth-shaped credential.

The project answers two ways to the same tool surface: an OAuth access token from
a real sign-in, and an API key of type `mcp` for a client that is a script rather
than a person. `MultiAuth` runs the token verifiers in order, so this sits beside
the proxy rather than inside it.

It exists as a class because an `AuthProvider` is a callable, and a bare function
would be the one piece of this layer with no name to hang off — which is how a
verifier ends up registered in two places and one of them stops being updated.

**The key arrives as `Authorization: Bearer`, not as `X-API-Key`.** That is a
change from the API-key-only version of this server. OAuth defines one header for
a bearer token and every MCP client sends that one, and FastMCP's auth middleware
runs before any middleware a caller adds — so a request carrying only
`X-API-Key` is refused before a normaliser could rewrite it. Accepting both would
mean wrapping the ASGI app outside what `run()` builds, which is a lot of fragile
arithmetic to preserve a second spelling of the same credential.
"""

from fastmcp.server.auth import AccessToken, TokenVerifier

from src.db import session_scope
# The prefix is a module constant, not a class attribute: it describes the shape
# of a plaintext key rather than anything about a row.
from src.models.api_key import KEY_PREFIX
from src.models import ApiKey, KeyType


class McpApiKeys(TokenVerifier):
  """Accepts an API key of type `mcp`, presented as a bearer token."""

  def __init__(self, base_url=None, resource_base_url=None):
    super().__init__(base_url=base_url, resource_base_url=resource_base_url)

  async def verify_token(self, token):
    """The `AccessToken` for a valid key, or None.

    Only `KeyType.MCP` is looked up, so an ordinary API key arrives here as an
    unknown key rather than as a forbidden one — the same reasoning as on
    `/api`, and for the same reason: a refusal should not confirm that somebody
    else's credential exists.

    The claim is deliberately thin. It carries the user id and nothing that could
    be mistaken for a permission, because everything this key can reach is scoped
    by `McpAuth` re-reading the user rather than by anything in the token.
    """
    if not token or not token.startswith(KEY_PREFIX):
      # An early-out, not a filter. Every key starts `sk_` whatever its type, so
      # this only skips a database query for the OAuth tokens, which is the
      # majority of what arrives once sign-in is in use.
      return None

    with session_scope() as db:
      key = ApiKey.find(db, token, KeyType.MCP)

      if key is None or not key.is_valid():
        return None

      # Recorded on every use, the same as the HTTP API's: `last_used_at` is how
      # an operator tells a key in active use from one nobody has presented.
      key.touch()
      db.commit()
      user = key.user

    return AccessToken(
      token=token,
      client_id=ApiKey.prefix_of(token),
      scopes=["mcp"],
      subject=str(user.id),
      claims={"sub": str(user.id), "usr": user.username, "via": "api_key"},
    )
