"""Who is calling the MCP server.

A tool call arrives with an access token, and the token says which user it is for.
That is the whole job, and it is the same job `Dependencies.get_current_user`
does on the HTTP API: turn a credential into a `User`, and refuse cleanly when
there is not one.

**Two credentials reach here.** `MultiAuth` accepts either an OAuth access token
from a real sign-in (see `authorization.py`) or an API key of type `mcp`, and
both end up as the same thing — an `AccessToken` carrying a user id. Nothing
downstream of `user()` knows or cares which one was used, which is the point:
there is one per-user client and one cart either way.

There is no fallback and no default user. A tool that cannot say whose cart it is
about would be guessing, and on this project guessing wrong means ordering from
somebody else's cart.
"""

from fastmcp.server.dependencies import get_access_token

from src.db import session_scope
from src.mcp.errors import McpAuthError
from src.models import User

#: Named in the message a refused tool call produces, because an agent that has
#: been refused is usually one whose client was configured without the header, and
#: the fix is a line of client config rather than anything this project repairs.
HOW_TO_AUTHENTICATE = (
  "Sign in to the MCP server, or present an MCP API key as the X-API-Key header "
  "(or `Authorization: Bearer <key>`). Create one with: "
  "python main.py apikey create --type mcp"
)


class McpAuth:
  """The user behind the access token on the current call, and their session."""

  @classmethod
  def user(cls):
    """The `User` this call is for.

    The user is **re-read from the database** rather than trusted from the token.
    A token is a claim about the past, and a deleted or demoted account has to
    lose access now rather than whenever the token happens to expire — which is
    the same rule `Dependencies.get_token_user` follows for a dashboard token.

    Raising rather than returning a refusal is deliberate: it is what makes the
    MCP client mark the call itself as failed, instead of handing back a
    successful tool result with an error string in the payload for a model to
    notice on its own.
    """
    token = get_access_token()

    if token is None:
      raise McpAuthError(f"No credentials on this MCP request. {HOW_TO_AUTHENTICATE}")

    subject = token.claims.get("sub") or token.subject

    if subject is None:
      raise McpAuthError(
        f"The access token names no account. {HOW_TO_AUTHENTICATE}"
      )

    try:
      user_id = int(subject)
    except (TypeError, ValueError):
      raise McpAuthError(
        "The access token's subject is not an account id, so the server cannot "
        "tell whose data this is. Sign in again."
      ) from None

    with session_scope() as db:
      user = User.get_by_id(db, user_id)

    if user is None:
      raise McpAuthError(
        "That account no longer exists. Sign in again with an account that does."
      )

    return user

  @classmethod
  def client(cls):
    """The caller's `Livewire`, so their tools read and edit their own cart.

    Cached per user for the life of the process, as it is for the HTTP API, so a
    burst of tool calls does not mean a burst of logins.
    """
    from src.utils.client_cache import ClientCache

    return ClientCache.get(cls.user().username)

  @classmethod
  def cart(cls):
    """The caller's `Cart`, built over their own `Livewire`.

    The counterpart of `Dependencies.get_cart`: the cart belongs to the site's
    session, so it belongs to a `Livewire`, which belongs to a user. Naming it
    here rather than at each call site keeps every cart tool reading one user's
    cart and makes that a property of the layer.
    """
    from src.services import Cart

    return Cart(client=cls.client())
