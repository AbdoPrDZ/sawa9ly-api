"""Who is calling the MCP server.

An MCP session has no user of its own. The process is long-lived and serves many
clients over one port, so the identity has to arrive with every request rather
than being fixed when the server starts. It does, as the same two headers the
HTTP API accepts — with one difference that is the whole reason `KeyType` exists:
only a key of type `mcp` is looked up here.

There is no fallback and no default user. A tool that cannot say whose cart it is
about would be guessing, and on this project guessing wrong means ordering from
somebody else's cart.
"""

from fastmcp.server.dependencies import get_http_headers

from src.db import session_scope
from src.models import ApiKey, KeyType
from src.mcp.errors import McpAuthError

#: Where the MCP server is listening, named in the message a refused tool call
#: produces. An agent that has been refused a key is usually one that was never
#: configured with the right header at all, and the fix is a line of client
#: config rather than anything this project can repair.
HOW_TO_AUTHENTICATE = (
  "Send an MCP API key as the X-API-Key header (or "
  "`Authorization: Bearer <key>`). Create one with: "
  "python main.py apikey create --type mcp"
)


class McpAuth:
  """The user behind the key on the current request, and their site session."""

  #: Lowercase, because that is how `get_http_headers` keys its result — it
  #: normalises every name, and looking a header up under the spelling the client
  #: sent is how a valid key silently reads as absent.
  HEADER = "x-api-key"

  #: `get_http_headers` withholds `authorization` unless a caller names it in
  #: `include`, on the grounds that a credential header should not be forwarded
  #: onward by accident. Here it is the credential, so it is asked for by name
  #: rather than by reaching for the whole request and bypassing the filter.
  ALLOWED = frozenset({"authorization"})

  @classmethod
  def user(cls):
    """The `User` the presented MCP key belongs to.

    A key of the wrong type is not found rather than rejected: an `api` key sent
    here gets the same "unknown key" as a string that was never a key, so this
    cannot be used to confirm that somebody else's credential exists.

    The lookup also records the use, exactly as the HTTP API does — `last_used_at`
    is how an operator tells a key in active use from one nobody has presented.
    Raising rather than returning a refusal is deliberate: it is what makes the
    MCP client mark the call itself as failed, instead of handing back a
    successful tool result with an error string in the payload for a model to
    notice on its own.
    """
    headers = get_http_headers(include=cls.ALLOWED)
    token = cls._token(headers)

    if not token:
      raise McpAuthError(f"No API key on this MCP request. {HOW_TO_AUTHENTICATE}")

    with session_scope() as db:
      key = ApiKey.find(db, token, KeyType.MCP)

      if key is None:
        raise McpAuthError(f"Unknown API key. {HOW_TO_AUTHENTICATE}")

      if not key.is_valid():
        raise McpAuthError(
          "This MCP key has been revoked or has expired. Revoke it and issue a "
          "new one, or drop the expiry."
        )

      key.touch()
      db.commit()

      # Read on the session that is about to close, so the relationship is loaded
      # before it goes: `expire_on_commit` is off, but the row is still detached
      # the moment the session closes and a lazy load would then raise.
      return key.user

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

  @classmethod
  def _token(cls, headers):
    """The key out of whichever of the two headers it arrived in.

    `X-API-Key` wins when both are present. They carry the same value in every
    normal request, so the only case where they differ is a client that got the
    headers backwards, and preferring the unambiguous one beats taking whichever
    came second.
    """
    if token := headers.get(cls.HEADER):
      return token

    scheme, _, value = headers.get("authorization", "").partition(" ")

    return value.strip() if scheme.lower() == "bearer" else None
