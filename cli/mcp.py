"""CLI: running the MCP server."""

from src.config import Config


class McpCli:
  """`mcp` — serve this project's operations to an AI agent over MCP.

  A process, not an action, so it needs a command to live in exactly as `serve`
  and `telegram listen` do.

  Defaults come from `Config` (MCP_HOST, MCP_PORT, MCP_PATH) and each can be
  overridden per run with a flag. There is no `--user`: the caller is whichever
  account's API key the MCP client was configured with, resolved per request, so
  the server has no user of its own to be told about. Create a key for it with
  `python main.py apikey create --type mcp` — an ordinary `api` key is refused
  here, which is what `KeyType` is for.
  """

  @staticmethod
  def register(commands):
    mcp = commands.add_parser('mcp', help="run the MCP server")
    mcp.add_argument('--host', default=Config.mcp_host(),
                     help=f"default {Config.MCP_HOST_VAR} or {Config.MCP_DEFAULT_HOST}")
    mcp.add_argument('--port', type=int, default=Config.mcp_port(),
                     help=f"default {Config.MCP_PORT_VAR} or {Config.MCP_DEFAULT_PORT}")
    mcp.add_argument('--path', default=Config.mcp_path(),
                     help=f"default {Config.MCP_PATH_VAR} or {Config.MCP_DEFAULT_PATH}")

  @staticmethod
  def dispatch(args):
    from src.logging_setup import Logging
    from src.mcp import McpServer

    # Before the server is built, not after. The same reason `ServeCli` does it:
    # uvicorn is about to install its own handlers over the root logger, and
    # unless it is told not to, every log file this project writes stays empty —
    # including the refusal a bad MCP key produces, which is exactly the line an
    # operator would come looking for.
    Logging.configure()

    McpServer.build().run(
      transport="http",
      host=args.host,
      port=args.port,
      path=args.path,
    )
