"""The MCP server: this project's operations, as tools.

A third front end, alongside the CLI and the HTTP API, over the same services.
It exists because an MCP client is a language model rather than a script, and
that changes three things and nothing else:

- **Authentication is per call, not per process.** A shell gets `--user`; an HTTP
  request gets the key on its headers, because one server serves every client.
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

from src.mcp.catalogue import CatalogueTools
# from src.mcp.cart import CartTools
# from src.mcp.checkout import CheckoutTools
# from src.mcp.clients import ClientsTools
# from src.mcp.orders import OrdersTools
from src.mcp.pages import PagesTools
from src.mcp.products import ProductsTools
# from src.mcp.telegram import TelegramTools
# from src.mcp.trackers import TrackersTools
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
  def build():
    """A `FastMCP` with every tool registered and the tables in place.

    `ensure_db` runs here rather than per tool, because this is the process
    boundary: every call after this one is a call against a database that
    already exists, exactly as `create_app` does for the API.
    """
    ensure_db()

    mcp = FastMCP(
      name="sawa9ly",
      instructions=INSTRUCTIONS,
      version=VERSION,
    )

    for group in TOOL_GROUPS:
      McpServer._register(mcp, group)

    return mcp

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
