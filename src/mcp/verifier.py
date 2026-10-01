"""Checking our own access tokens, for `OAuthProxy`.

A short, easily-missed piece of the arrangement. `OAuthProxy` does not hand this
verifier the token the client sent: the client holds a *reference* JWT whose only
real claim is a `jti`. FastMCP resolves that `jti` to the upstream token and
calls us with **that** — ours, the one `authorization.py` signed. So verifying it
is a signature check and a claim read, with no lookup table and no introspection
endpoint.

The one thing it must not do is trust the claims for authorisation. It returns
the user id and stops; `McpAuth` re-reads the user from the database, so an
account deleted a second ago loses access immediately rather than when its token
happens to expire.
"""

from fastmcp.server.auth import AccessToken, TokenVerifier

from src.mcp.authorization import AuthorizationServer


class McpTokens(TokenVerifier):
  """Accepts an access token this project signed, and nothing else."""

  def __init__(self, base_url=None, resource_base_url=None):
    super().__init__(base_url=base_url, resource_base_url=resource_base_url)

  async def verify_token(self, token):
    """The `AccessToken` for a valid, unexpired access token, or None.

    A refresh token is refused here, and `AuthorizationServer` refuses it before
    this is reached — the type is in the token, so promoting one is an argument
    somebody would have to change rather than a check somebody would have to
    remember.

    Nothing is logged here. A token is a credential, and this is the function
    that most obviously wants to log the thing it was handed.
    """
    if not token:
      return None

    payload = AuthorizationServer.verify_access_token(token)

    if payload is None:
      return None

    subject = payload.get("sub")

    if subject is None:
      return None

    return AccessToken(
      token=token,
      # The MCP client's own id is not in an upstream token, and the proxy puts
      # it on the reference token instead. Naming the issuer is honest here
      # rather than inventing a client id nobody registered.
      client_id=AuthorizationServer.ISSUER,
      scopes=["mcp"],
      subject=str(subject),
      claims={"sub": str(subject), "usr": payload.get("usr"), "via": "oauth"},
    )
