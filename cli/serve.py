"""CLI: running the HTTP API."""

from src.config import Config


class ServeCli:
  """`serve` - start the FastAPI app.

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
                       help="reload on code changes (default {0})".format(Config.RELOAD_VAR))

  @staticmethod
  def dispatch(args):
    import uvicorn

    from cli.base import Cli
    from src.logging_setup import UVICORN_LOG_CONFIG, Logging

    # uvicorn installs its own handlers over the root logger unless told not to,
    # which would leave every log file empty no matter what Config says. This is
    # why `main.py serve` now honours LOG_LEVEL and LOG_DIR at all: the
    # `python -m src.server` path always did, this one did not.
    Logging.configure()

    # Before the app is built, so an occupied port costs a sentence rather than
    # an opened database and a banner.
    Cli.assert_port_free(args.host, args.port)

    uvicorn.run(
      "src.server:app",
      host=args.host,
      port=args.port,
      reload=args.reload,
      log_config=UVICORN_LOG_CONFIG,
    )
