"""CLI: running the HTTP API."""

from src.config import Config


class ServeCli:
  """`serve` — start the FastAPI app.

  Defaults come from `Config` (API_HOST, API_PORT, API_RELOAD) and each can be
  overridden per run with a flag.
  """

  @staticmethod
  def register(commands):
    serve = commands.add_parser('serve', help="run the HTTP API and dashboard")
    serve.add_argument('--host', default=Config.host(),
                       help=f"default {Config.HOST_VAR} or {Config.DEFAULT_HOST}")
    serve.add_argument('--port', type=int, default=Config.port(),
                       help=f"default {Config.PORT_VAR} or {Config.DEFAULT_PORT}")
    serve.add_argument('--reload', action='store_true', default=Config.reload(),
                       help=f"reload on code changes (default {Config.RELOAD_VAR})")

  @staticmethod
  def dispatch(args):
    import uvicorn

    uvicorn.run("src.server:app", host=args.host, port=args.port, reload=args.reload)
