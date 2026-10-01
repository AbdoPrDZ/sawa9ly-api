"""The MCP server: this project's operations, as tools.

A third front end, alongside the CLI and the HTTP API, over the same services.
It exists because an MCP client is a language model rather than a script, and
that changes four things and nothing else:

- **Authentication is an OAuth sign-in or an API key.** A shell gets `--user`; a
  request gets a bearer token, because one server serves every client. See
  `auth.py`, and `authorization.py` for the sign-in behind it.
- **Failures are raised, not returned.** There is no status code here, so the
  error message is all the model gets. See `errors.py`.
- **Descriptions are the interface.** A tool's docstring is its schema's prose,
  so it has to say what the tool is *for* and not just restate the argument names.

The tool set is written one module per `/api/v1` resource, and `TOOL_GROUPS` below
is the switchboard: a resource is served when it is in that tuple, and not
otherwise. The mirroring rule is the same one that binds the CLI to the API — an
operation in one and not the others is unfinished work — so turning a group on is
the whole of adding a resource, and leaving one off is a deliberate narrowing
rather than a gap.

Running it is `python main.py mcp`, which is a command in `cli/mcp.py` and not
anything in this package — the package builds the server, the command serves it.
"""

from fastmcp import FastMCP
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.oauth_proxy import OAuthProxy

from src.config import Config
from src.mcp.api_keys import McpApiKeys
from src.mcp.authorization import AuthorizationServer
from src.mcp import handlers
from src.mcp.catalogue import CatalogueTools
# from src.mcp.cart import CartTools
# from src.mcp.checkout import CheckoutTools
# from src.mcp.clients import ClientsTools
from src.mcp.pages import PagesTools
# from src.mcp.orders import OrdersTools
from src.mcp.products import ProductsTools
# from src.mcp.telegram import TelegramTools
# from src.mcp.trackers import TrackersTools
from src.mcp.verifier import McpTokens
from src.utils.livewire import ensure_db
from src.version import VERSION

#: The instructions the client shows the model before it sees any tool.
#:
#: Kept in step with `TOOL_GROUPS` deliberately: this is text handed to a language
#: model, and a model told about a tool that is not registered will ask for it and
#: get "no such tool", which it has to work around rather than being told plainly.
#: So there is nothing here about a cart or about ordering — the resources that
#: would carry those are written but not switched on. When one is, its checkout
#: warning belongs here, because an order placed on sawa9ly.app cannot be
#: cancelled from here.
INSTRUCTIONS = """\
Read-only tools for sawa9ly.app, an Algerian dropshipping site: look up a product
page, keep a catalogue of what you have seen, and write landing pages.

Every tool acts for the account whose API key this client was configured with —
not for the operator — and can reach that account's data and nothing else.

There is no tool that changes a cart or places an order, so nothing you can call
here spends money or creates an order on the site.
"""

#: The resources this server serves, in the order `create_app` mounts the
#: corresponding controllers.
#:
#: **Not all of `/api/v1` is here.** `cart`, `checkout`, `clients`, `orders`,
#: `telegram` and `trackers` have their modules written and are commented out
#: below; the ones listed are what the server actually exposes. Turning one on is
#: uncommenting its import and its entry here, and nothing else — the module, the
#: auth and the per-key scoping are already there.
#:
#: The cart and order resources are the deliberate half to leave off first: they
#: are the ones that can spend money, and an order placed on sawa9ly.app cannot be
#: cancelled from here.
TOOL_GROUPS = (
  ProductsTools,
  # CartTools,
  # CheckoutTools,
  CatalogueTools,
  # ClientsTools,
  # OrdersTools,
  PagesTools,
  # TelegramTools,
  # TrackersTools,
)


class McpServer:
  """The assembled MCP server, and the one place its tool set is written down.

  `build()` rather than a module-level instance, for the reason
  `cli/router.py` defers its import of `src.server`: building the server touches
  the database, and something that has to be asked for explicitly is something
  the other hundred CLI commands cannot accidentally trigger.
  """

  @staticmethod
  def build(public_url=None, path=None):
    """A `FastMCP` with every tool registered, the tables in place and auth on.

    `ensure_db` runs here rather than per tool, because this is the process
    boundary: every call after this one is a call against a database that
    already exists, exactly as `create_app` does for the API.

    `public_url` is the origin Claude connects to, which is not the address this
    process binds — see `Config.mcp_public_url`. `path` is where the transport is
    mounted, and both the proxy and our own authorize endpoint have to agree on it.
    """
    ensure_db()

    public_url = (public_url or Config.mcp_public_origin()).rstrip("/")
    path = path or Config.mcp_path()
    authorization = AuthorizationServer(public_url)
    client_id, client_secret = authorization.credentials()

    mcp = FastMCP(
      name="sawa9ly",
      instructions=INSTRUCTIONS,
      version=VERSION,
      auth=MultiAuth(
        server=OAuthProxy(
          # The upstream is this project: `authorization.py` is the sign-in page
          # and the token endpoint. FastMCP does the whole protocol on the way
          # in and on the way out, and this is the part that knows a password.
          upstream_authorization_endpoint=authorization.authorize_url,
          upstream_token_endpoint=authorization.token_url,
          upstream_client_id=client_id,
          upstream_client_secret=client_secret,
          token_verifier=McpTokens(),
          # The origin, never the mount path: FastMCP appends `mcp_path` to this
          # to get the resource identifier, so passing the full path yields
          # `.../mcp/mcp/` and every authorize request is rejected as a resource
          # mismatch. Cost me an afternoon once; it is commented here so it does
          # not cost it again.
          base_url=public_url,
          resource_base_url=public_url,
          # `external` says the consent decision is the upstream's, which is the
          # sign-in itself: a person who typed their password has consented.
          # The default would show the proxy's own consent page between them and
          # the login, asking about a decision they have already made.
          require_authorization_consent="external",
        ),
        # The API key, accepted as a bearer token so a scripted client keeps
        # working. Ordered after the proxy: a key is checked against the database
        # on every call, and the sign-in path should not pay for that.
        verifiers=[McpApiKeys()],
        base_url=public_url,
        resource_base_url=public_url,
      ),
    )

    McpServer._register_sign_in(mcp, authorization)

    for group in TOOL_GROUPS:
      McpServer._register(mcp, group)

    return mcp

  @staticmethod
  def app(public_url=None, path=None):
    """The ASGI application, for a caller that wants to serve it itself.

    `build()` plus the transport. `cli/mcp.py` uses `build().run()`; this is here
    for the tests and for anything that wants the app without uvicorn.
    """
    mcp = McpServer.build(public_url=public_url, path=path)

    return mcp.http_app(path=path or Config.mcp_path())

  @staticmethod
  def _register_sign_in(mcp, authorization):
    """Add our authorize and token endpoints to the server.

    FastMCP mounts its own OAuth routes — `/authorize`, `/token`, `/register` —
    and ours go beside them. The proxy redirects a person to
    `authorization.authorize_url`, so that has to be served by *this* process on
    *this* port for the redirect to land anywhere at all. Both being on one public
    origin is what lets there be a single URL to give Claude and a single origin
    to put behind TLS.

    Registered with `custom_route` rather than by appending to the ASGI app's
    route list: `run()` builds the app itself, so anything added to a
    separately-built app would not be there when it matters.
    """
    prefix = authorization.path_prefix

    # Closed over rather than read off `request.app.state`, because a custom
    # route's app is FastMCP's and not ours to put things on.
    async def authorize(request):
      return await handlers.authorize(request, authorization)

    async def token(request):
      return await handlers.token(request, authorization)

    mcp.custom_route(f"{prefix}/authorize", methods=["GET", "POST"])(
      authorize
    )
    mcp.custom_route(f"{prefix}/token", methods=["POST"])(token)

  @staticmethod
  def _register(mcp, group):
    """Add one resource's tools.

    The tool's public name is the method's own, so it is written down once, next
    to the docstring that describes it — and every name is unique across the
    groups, because FastMCP keys its registry by name and two `read` methods in
    different resources would be one tool.
    """
    for tool in group.tools():
      mcp.add_tool(tool)
