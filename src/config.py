"""Every environment variable this project reads, in one place.

Configuration is scattered by nature: a database URL in one module, a port in
another, a credential in a third. It is gathered here so there is a single file
to read to learn what can be set, a single place to add a variable, and no
module that reaches into `os.environ` on its own.

The rules this file follows:

- Nothing here is read at import time except the names. Values are read through
  methods, so a test or a tool can change the environment and re-read.
- A variable is documented on the attribute that reads it.
- Defaults are chosen so that `python main.py` works with no `.env` at all.
"""

import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()


class Config:
  """The project's environment, grouped by what it configures."""

  PROJECT_ROOT = Path(__file__).resolve().parents[1]

  DATA_DIR_VAR = "DATA_DIR"
  """Where the application keeps its working files that are not the database and
    not the logs: currently the queue's and the bot's lock files.

    Unset, it is `data/` beside the source. Relative values are resolved against
    the project root, so `data` and `./data` mean the same thing however the
    command was invoked.

    The database and the logs each have their own setting, because they are
    different kinds of thing: the database is the state to back up, the logs are
    large and disposable, and the locks are ephemeral and worthless once the
    process holding them has gone. Putting all three in one directory makes
    backing up any of them mean keeping the other two."""

  DATABASE_DIR_VAR = "DATABASE_DIR"
  """Where the SQLite file lives. Default `database/` beside the source.

    Only consulted for SQLite. A PostgreSQL or MySQL database is a server's
    business and this setting has no meaning there."""

  LOCK_DIR_VAR = "LOCK_DIR"
  """Where the queue's and the bot's lock files are created. Default: the data
    directory.

    A lock file only means anything while the process holding it is alive, and it
    is a `O_EXCL` create rather than a flock, so one left behind by a killed
    process is a stale file to be told about rather than a lock to be waited on.
    `/tmp` is the honest place for that under Docker, where the container's
    writable layer is thrown away with the container and nothing needs to survive
    it."""

  DEFAULT_DATA_DIR = "data"
  DEFAULT_DATABASE_DIR = "database"

  @classmethod
  def _resolve(cls, raw):
    """A configured path, absolute as given and project-relative otherwise."""
    path = Path(raw)

    if not path.is_absolute():
      path = cls.PROJECT_ROOT / path

    return path

  @classmethod
  def data_dir(cls):
    """Where the working files that are neither database nor logs are kept.

    Deliberately a method and not a class attribute. An attribute would have to
    be computed in the class body, which is import time: the value would then be
    frozen before anything could set the environment, and calling a classmethod
    from a class body is not even possible, because at that point it is still a
    `classmethod` object rather than a bound method. Reading the environment when
    the question is asked is both the thing that makes the location configurable
    and the only version of this that works.
    """
    return cls._resolve(os.getenv(cls.DATA_DIR_VAR) or cls.DEFAULT_DATA_DIR)

  @classmethod
  def database_dir(cls):
    """Where the SQLite file is created, if it is not named outright."""
    return cls._resolve(os.getenv(cls.DATABASE_DIR_VAR) or cls.DEFAULT_DATABASE_DIR)

  @classmethod
  def lock_dir(cls):
    """Where the queue's and the bot's lock files are created.

    No default of its own: it falls back to the data directory, so setting
    `DATA_DIR` moves the locks too and a deployment that has set only that stays
    self-consistent.
    """
    raw = os.getenv(cls.LOCK_DIR_VAR)

    return cls._resolve(raw) if raw else cls.data_dir()

  # There is no default-user *setting*. `--user` is optional and falls back to
  # the super admin, but that account is read from the database rather than
  # configured here, so nothing in the environment can quietly redirect a command
  # onto an account nobody named. See `Cli.super_username` for why an ambiguous
  # installation is refused rather than guessed at.

  # --- database -------------------------------------------------------

  DATABASE_URL_VAR = "DATABASE_URL"
  """A full URL. Wins over everything below, for a connection string you do
    not want to assemble from parts."""

  SQLITE_FILE_VAR = "SQLITE_FILE"
  """Where the SQLite file lives. Default: `data/sawa9ly.db`."""

  DB_DRIVER_VAR = "DB_DRIVER"
  """`sqlite` (default), `postgresql` or `mysql`. Only used when `DB_NAME` is
    set, since SQLite is a file rather than a host."""

  DB_HOST_VAR = "DB_HOST"
  DB_PORT_VAR = "DB_PORT"
  DB_NAME_VAR = "DB_NAME"
  DB_USER_VAR = "DB_USER"
  DB_PASSWORD_VAR = "DB_PASSWORD"

  #: Default port per driver, so `DB_HOST` + `DB_NAME` is enough for a server.
  DRIVER_PORTS = {"postgresql": 5432, "mysql": 3306, "sqlite": None}

  @classmethod
  def database_url(cls):
    """The SQLAlchemy URL, from `DATABASE_URL`, from parts, or SQLite.

    Falling back to a local SQLite file is what lets the project run with no
    configuration at all.
    """
    url = os.getenv(cls.DATABASE_URL_VAR)

    if url:
      return url

    name = os.getenv(cls.DB_NAME_VAR)

    if name:
      return cls._server_database_url(name)

    return cls.sqlite_url()

  @classmethod
  def sqlite_url(cls):
    """The default file database, in `database/`.

    The directory is created here rather than at import time, so importing
    `Config` never has the side effect of touching the filesystem.
    """
    path = Path(os.getenv(cls.SQLITE_FILE_VAR) or (cls.database_dir() / "sawa9ly.db"))

    if not path.is_absolute():
      path = cls.PROJECT_ROOT / path

    path.parent.mkdir(parents=True, exist_ok=True)

    return f"sqlite:///{path.as_posix()}"

  @classmethod
  def _server_database_url(cls, name):
    """Assemble a URL from the discrete DB_* variables."""
    driver = (os.getenv(cls.DB_DRIVER_VAR) or "postgresql").lower()
    host = os.getenv(cls.DB_HOST_VAR) or "localhost"
    port = os.getenv(cls.DB_PORT_VAR) or cls.DRIVER_PORTS.get(driver)
    user = os.getenv(cls.DB_USER_VAR)
    password = os.getenv(cls.DB_PASSWORD_VAR)

    if driver == "sqlite":
      return f"sqlite:///{name}"

    # url-encode the credentials: a password with an `@` or a `/` in it would
    # otherwise produce a URL that parses into the wrong place.
    from urllib.parse import quote_plus

    scheme = "postgresql" if driver == "postgresql" else "mysql"
    credentials = f"{quote_plus(user)}:{quote_plus(password)}@" if user else ""
    location = f"{host}:{port}" if port else host

    return f"{scheme}://{credentials}{location}/{name}"

  @classmethod
  def is_sqlite(cls):
    return cls.database_url().startswith("sqlite")

  # --- http server ----------------------------------------------------

  HOST_VAR = "API_HOST"
  PORT_VAR = "API_PORT"
  RELOAD_VAR = "API_RELOAD"

  DEFAULT_HOST = "127.0.0.1"
  DEFAULT_PORT = 8000

  @classmethod
  def host(cls):
    return os.getenv(cls.HOST_VAR) or cls.DEFAULT_HOST

  @classmethod
  def port(cls):
    return cls.as_int(cls.PORT_VAR, cls.DEFAULT_PORT)

  @classmethod
  def reload(cls):
    return cls.as_bool(cls.RELOAD_VAR, False)

  # --- mcp server -----------------------------------------------------

  MCP_HOST_VAR = "MCP_HOST"
  MCP_PORT_VAR = "MCP_PORT"
  MCP_PATH_VAR = "MCP_PATH"
  MCP_PUBLIC_URL_VAR = "MCP_PUBLIC_URL"
  MCP_FORWARDED_ALLOW_IPS_VAR = "MCP_FORWARDED_ALLOW_IPS"

  MCP_DEFAULT_HOST = "127.0.0.1"
  MCP_DEFAULT_PORT = 8001
  MCP_DEFAULT_PATH = "/mcp/"

  """A server of its own, on a port of its own.

    Deliberately not the API's host and port, and not mounted under /api. The MCP
    server authenticates with different credentials, so it is a separate
    process answering on a separate port: binding it beside the API would mean
    one restart takes both down, and putting it under /api would put a second
    credential on a path that is already public contract.

    `127.0.0.1` because an MCP client is normally another process on the same
    machine — a desktop agent, an IDE — and a tool surface that can place orders
    has no business listening on every interface by default."""

  @classmethod
  def mcp_host(cls):
    return os.getenv(cls.MCP_HOST_VAR) or cls.MCP_DEFAULT_HOST

  @classmethod
  def mcp_port(cls):
    return cls.as_int(cls.MCP_PORT_VAR, cls.MCP_DEFAULT_PORT)

  @classmethod
  def mcp_path(cls):
    """The path the streamable-HTTP transport is mounted at.

    A path rather than a bare port, because MCP over HTTP is a single
    streamable endpoint and a client needs to be told where it is. The trailing
    slash is not cosmetic: the mount is a prefix, and `/mcp` without one answers
    a redirect that some clients will not follow.
    """
    return os.getenv(cls.MCP_PATH_VAR) or cls.MCP_DEFAULT_PATH

  @classmethod
  def mcp_public_url(cls):
    """The origin Claude connects to, e.g. `https://mcp.example.com`.

      **Required for OAuth, and not the same thing as `MCP_HOST`.** OAuth hands
      the client a set of absolute URLs to redirect to and exchange tokens with,
      and a redirect pointing at the container's own address is a browser that
      cannot reach it. So this is the address the *outside world* uses, which is
      whatever tunnel or reverse proxy fronts the port — and it must be
      `https`, because a remote MCP connector refuses anything else.

      Unset, it falls back to the local bind address, which is enough for a
      client on this machine and silently wrong for a public one. The server says
      so on startup rather than letting a redirect go nowhere.
    """
    return (os.getenv(cls.MCP_PUBLIC_URL_VAR) or "").rstrip("/") or None

  @classmethod
  def mcp_public_origin(cls):
    """`mcp_public_url`, or the local bind address when it is unset."""
    return cls.mcp_public_url() or f"http://{cls.mcp_host()}:{cls.mcp_port()}"

  #: Loopback plus the private ranges, which is loopback plus whatever Docker
  #: bridge or LAN reverse proxy sits in front of the port.
  #:
  #: Not `*`, though that would be one less thing to configure: a trusted proxy
  #: is allowed to assert the scheme and the client address, so trusting the whole
  #: internet would let any caller claim to be a request that arrived over TLS.
  #: These ranges are the ones a proxy on the same machine or network can have.
  MCP_DEFAULT_FORWARDED_ALLOW_IPS = (
    "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
  )

  @classmethod
  def mcp_forwarded_allow_ips(cls):
    """Which proxies' `X-Forwarded-*` headers to believe.

      **This is the reason a redirect can come back as `http://`.** uvicorn reads
      `X-Forwarded-Proto` only from a proxy it trusts, and its own default is
      loopback alone. Behind a Docker bridge the request arrives from the
      gateway, the header is ignored, the ASGI scope still says `http`, and
      every `Location` the app builds — including the trailing-slash redirect a
      client hits when it normalises `/mcp` to `/mcp/` — points at cleartext. The
      symptom is a connector that authorizes successfully and then cannot connect,
      because following the redirect would downgrade and re-send a bearer token.

      Set it to a single address to tighten it. `*` works and trusts anything,
      which is only defensible when nothing else can reach the port.
    """
    return (
      os.getenv(cls.MCP_FORWARDED_ALLOW_IPS_VAR)
      or cls.MCP_DEFAULT_FORWARDED_ALLOW_IPS
    )

  # --- logging --------------------------------------------------------

  LOG_LEVEL_VAR = "LOG_LEVEL"
  """`debug`, `info` (default), `warning`, `error` or `critical`.

    `info` rather than `warning`, because the queue and the bot are the two things
    you run in the background and then never see again: their pass summaries and
    their per-event lines are the only record that they ran at all. Raise this to
    quiet them, and note that the HTTP access log is unaffected - see
    `logging_setup`, which pins that one deliberately."""

  LOG_DIR_VAR = "LOG_DIR"
  """Where the per-subsystem log files go. Default `logs/` beside the source.

    Set it to an absolute path to put them somewhere else - `/var/log/sawa9ly`
    under Docker, which is where a Linux system keeps logs and where a volume is
    expected to be mounted for them.

    One file per subsystem - api, dashboard, cli, cron, telegram - so a failure in
    one does not have to be read out of the others. Files appear only when
    something is written to them, so a quiet day leaves none behind."""

  LOG_FILE_VAR = "LOG_FILE"
  """Optional. A single file receiving everything, instead of the five.

    For whoever wants one stream, or wants it somewhere else. It replaces the
    per-subsystem files rather than adding to them; two copies of every line is
    worse than either."""

  LOG_FORMAT_VAR = "LOG_FORMAT"
  """`text` (default) or `json` for structured lines."""

  DEFAULT_LOG_LEVEL = "INFO"
  DEFAULT_LOG_DIR = "logs"

  @classmethod
  def log_level(cls):
    return (os.getenv(cls.LOG_LEVEL_VAR) or cls.DEFAULT_LOG_LEVEL).upper()

  @classmethod
  def log_dir(cls):
    """The directory the per-subsystem log files live in.

    Resolved against the project root, not the data directory, so the default is
    `logs/` beside the source - logs in their own place, next to the database
    rather than inside it. Absolute when set, which is how a container puts them
    under `/var/log`.
    """
    return cls._resolve(os.getenv(cls.LOG_DIR_VAR) or cls.DEFAULT_LOG_DIR)

  @classmethod
  def log_file(cls):
    """A single file receiving every log line, instead of the five.

    Resolved against the data directory when relative, and None when unset.
    """
    raw = os.getenv(cls.LOG_FILE_VAR)

    if not raw:
      return None

    return cls._resolve(raw)

  @classmethod
  def log_format(cls):
    return (os.getenv(cls.LOG_FORMAT_VAR) or "text").lower()

  @classmethod
  def log_configured(cls):
    """Whether the operator asked for more logging than the default.

    Logging stays off unless asked for, so a normal run prints only what
    matters: errors and the server's own startup lines.
    """
    return bool(os.getenv(cls.LOG_FILE_VAR)) or cls.log_level() != cls.DEFAULT_LOG_LEVEL

  # --- dashboard ------------------------------------------------------

  DASHBOARD_SECRET_VAR = "DASHBOARD_SECRET"
  """Signing key for dashboard tokens. Generated and stored if unset."""

  @classmethod
  def dashboard_secret(cls):
    return os.getenv(cls.DASHBOARD_SECRET_VAR)

  SUPER_ADMIN_USERNAME_VAR = "SUPER_ADMIN_USERNAME"
  SUPER_ADMIN_PASSWORD_VAR = "SUPER_ADMIN_PASSWORD"
  """Both required on a database with no super account; there is no default."""

  @classmethod
  def super_username(cls):
    return os.getenv(cls.SUPER_ADMIN_USERNAME_VAR)

  @classmethod
  def super_password(cls):
    return os.getenv(cls.SUPER_ADMIN_PASSWORD_VAR)

  # --- cron / tracking queue -------------------------------------------

  CRON_INTERVAL_VAR = "CRON_INTERVAL"
  """Seconds between queue passes. Default 300, i.e. every five minutes."""

  CRON_DELAY_VAR = "CRON_DELAY"
  """Seconds to wait between two target fetches. The queue hits the live site
    once per tracked product, and going slowly is what keeps it a guest rather
    than a load. Default 1.0."""

  DEFAULT_CRON_INTERVAL = 300
  DEFAULT_CRON_DELAY = 1.0

  @classmethod
  def cron_interval(cls):
    return cls.as_int(cls.CRON_INTERVAL_VAR, cls.DEFAULT_CRON_INTERVAL)

  @classmethod
  def cron_delay(cls):
    raw = os.getenv(cls.CRON_DELAY_VAR)

    if raw is None or raw == "":
      return cls.DEFAULT_CRON_DELAY

    try:
      return max(0.0, float(raw))
    except ValueError:
      raise ValueError(
        f"{cls.CRON_DELAY_VAR} must be a number of seconds, got {raw!r}"
      ) from None

  # --- telegram -------------------------------------------------------

  TELEGRAM_BOT_TOKEN_VAR = "TELEGRAM_BOT_TOKEN"
  """The bot's token from @BotFather. Optional: without it the Telegram
    integration is simply off, and nothing else in the project needs it."""

  TELEGRAM_BOT_NAME_VAR = "TELEGRAM_BOT_NAME"
  """The bot's @username, for building a `t.me` link.

    A fallback only. The real name comes from `getMe`, which reads it off the
    token itself, so a link can never name a bot the token does not belong to.
    This exists for the case where Telegram cannot be reached to ask."""

  #: How long a binding code stays usable. Short on purpose: it is a bearer
  #: credential, and whoever sends it first gets the binding.
  TELEGRAM_CODE_TTL_SECONDS = 15 * 60

  #: Seconds a `telegram listen` poll waits for updates before returning. 30
  #: keeps each request short enough that a second poller cannot hold the
  #: connection open long enough to look like the only one.
  TELEGRAM_POLL_TIMEOUT = 30

  #: Back-off after Telegram's 409, which it returns when a token is polled
  #: twice. Telegram appears to keep per-token poll state for a while after a
  #: poller exits, so a restart can hit this for up to a minute even when only
  #: one process is running.
  TELEGRAM_CONFLICT_BACKOFF = 30

  @classmethod
  def telegram_token(cls):
    return os.getenv(cls.TELEGRAM_BOT_TOKEN_VAR) or None

  @classmethod
  def telegram_bot_name(cls):
    """The bot's @username, without the leading `@`."""
    name = os.getenv(cls.TELEGRAM_BOT_NAME_VAR) or ""

    return name.lstrip("@").strip() or None

  @classmethod
  def telegram_configured(cls):
    """Whether a bot token is available.

    Checked rather than assumed, so every entry point can refuse with something
    actionable — "set TELEGRAM_BOT_TOKEN" — instead of failing on a None token
    somewhere inside an HTTP call.
    """
    return bool(cls.telegram_token())

  # --- parsing --------------------------------------------------------

  @classmethod
  def as_int(cls, variable, default):
    raw = os.getenv(variable)
    if raw is None or raw == "":
      return default
    try:
      return int(raw)
    except ValueError:
      raise ValueError(
        f"{variable} must be a whole number, got {raw!r}"
      ) from None

  @staticmethod
  def as_bool(variable, default=False):
    """Read a boolean from the environment.

    `bool(os.getenv(...))` is wrong — it makes the string "false" true — so the
    usual truthy and falsy words are recognised instead.
    """
    raw = os.getenv(variable)

    if raw is None or raw == "":
      return default

    return raw.strip().lower() in ("1", "true", "yes", "on")
