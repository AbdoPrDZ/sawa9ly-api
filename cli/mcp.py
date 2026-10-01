"""CLI: running the MCP server."""

from src.config import Config


class McpCli:
  """`mcp` — serve this project's operations to an AI agent over MCP.

  A process, not an action, so it needs a command to live in exactly as `serve`
  and `telegram listen` do.

  Defaults come from `Config` (MCP_HOST, MCP_PORT, MCP_PATH) and each can be
  overridden per run with a flag.

  **The host and the port are not the address Claude uses.** OAuth hands a client
  absolute URLs to redirect to, and a redirect naming the container's own address
  is a browser that cannot follow it, so `MCP_PUBLIC_URL` names the public origin
  and is required for anything but a client on this machine. This command says so
  on startup rather than letting a sign-in redirect go nowhere.
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
    mcp.add_argument('--public-url', default=Config.mcp_public_url(),
                     help="the origin clients connect to, e.g. "
                          "https://mcp.example.com "
                          f"(default {Config.MCP_PUBLIC_URL_VAR})")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.logging_setup import Logging
    from src.mcp import McpServer

    # Before the server is built, not after. The same reason `ServeCli` does it:
    # uvicorn is about to install its own handlers over the root logger, and
    # unless it is told not to, every log file this project writes stays empty —
    # including the refusal a bad credential produces, which is exactly the line
    # an operator would come looking for.
    Logging.configure()

    # Before anything is built, so an occupied port costs a sentence rather than
    # a database open and a banner. `--port` is the flag to change.
    Cli.assert_port_free(args.host, args.port)

    public_url = McpCli._public_url(args)
    McpCli._report(args, public_url)

    McpServer.build(public_url=public_url, path=args.path).run(
      transport="http",
      host=args.host,
      port=args.port,
      path=args.path,
    )

  @staticmethod
  def _public_url(args):
    """The origin to advertise, with a trailing slash removed.

    Normalised here rather than trusted: a trailing slash in this value ends up
    as `//` in every URL handed to a client, and `https://host//oauth/authorize`
    is a 404 that looks like a routing problem.
    """
    return (args.public_url or f"http://{args.host}:{args.port}").rstrip("/")

  @staticmethod
  def _report(args, public_url):
    """Print where the connector goes, and say so if it will not work.

    On stderr, because it is addressed to whoever started the process and not to
    whatever the process is doing. Two things are worth saying: the URL to paste
    into the connector, and whether that URL is one a client could reach — a
    remote connector refuses plain HTTP, and finding that out from Claude's error
    message is a worse way to learn it than reading it here.
    """
    import sys

    if Config.mcp_public_url() is None:
      sys.stderr.write(
        f"{Config.MCP_PUBLIC_URL_VAR} is not set, so this server is advertising "
        f"{public_url}.\n"
        "  That works for a client on this machine. Claude and other remote "
        "connectors need HTTPS, so set\n"
        f"  {Config.MCP_PUBLIC_URL_VAR}=https://your-host and put a tunnel or "
        "reverse proxy in front of it.\n"
      )
    elif not public_url.startswith("https://"):
      sys.stderr.write(
        f"warning: {Config.MCP_PUBLIC_URL_VAR} is {public_url}, which is not "
        "HTTPS.\n  Claude and other remote connectors refuse it. Sign-in will "
        "work for a local client and fail for a remote one.\n"
      )

    sys.stderr.write(f"MCP connector URL: {public_url}{args.path}\n")
    sys.stderr.flush()
