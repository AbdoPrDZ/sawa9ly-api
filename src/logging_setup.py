"""Logging setup.

The project logs through the standard library rather than adding a logging
framework. What is configurable comes from `Config`: the level, where the files
go, and plain or JSON formatting.

**One file per subsystem.** The api, the dashboard, the CLI, the queue and the bot
run separately and fail separately, so each gets its own file. Reading a failed
checkout out of a log that also has every scraped product page in it is the
problem this solves. `LOG_FILE` replaces the five with one for whoever wants a
single stream; the files are created only when something is written, so a quiet
day leaves none behind.

**Routing is by logger name, not by process.** A `cron listen` and a
`telegram listen` are separate processes, but `serve` is one process serving both
the API and the dashboard, and the CLI is a hundred short-lived processes that
touch everything. Deciding by logger name means the split holds no matter which
process a line came from, and a line cannot end up in two files because two
prefixes happened to match it.

Three decisions worth stating, because all are deliberate:

- **The HTTP access log is pinned to INFO, whatever `LOG_LEVEL` says.** It is a
  fixed, high-value record of who called what, and the whole point of an api log
  is that it shows traffic. Turning the level up to quiet an application's own
  debugging should not silently delete the access history. Nothing is lost: a
  quieter level only means fewer of the project's *own* lines.
- **`LOG_LEVEL` defaults to INFO, not WARNING.** The queue and the bot are run in
  the background and then never seen again; their pass summaries and per-event
  lines are the only evidence they ran at all.
- **Credentials are never logged.** The value after any secret-looking field is
  replaced, because the project handles passwords, tokens and cookies, and a stray
  log line would otherwise put one in a file that is read and pasted around.

`Logging.configure()` is what sets this up, and is called by every command.
"""

import json
import logging
import re
import sys
from pathlib import Path

from src.config import Config

#: The five subsystems, and the logger names that belong to each.
#:
#: A logger belongs to the **first** entry whose prefixes match, so order matters
#: and is the tie-break: `src.services.telegram` would otherwise be swallowed by a
#: broader `src.services` prefix. The list is deliberately explicit rather than
#: derived from the module tree, because "which log does this belong in" is a
#: decision somebody has to make, and a default nobody chose is not a decision.
SUBSYSTEMS = (
  (
    "telegram",
    ("src.utils.telegram", "src.services.telegram", "src.models.telegram_binding"),
  ),
  (
    "cron",
    (
      "src.services.cron",
      "src.services.tracking",
      "src.services.order_sync",
      "src.services.notifications",
    ),
  ),
  (
    "cli",
    ("cli",),
  ),
  (
    "dashboard",
    # The dashboard's own logger, fed by the request middleware in
    # `src/controllers/dashboard_log.py`. Deliberately narrow: it names the
    # browser-facing routes, not everything served by the same process.
    ("src.controllers.dashboard_log",),
  ),
  (
    "api",
    (
      "src.server",
      "src.db",
      "src.controllers",
      "src.services",
      "src.utils",
      "sawa9ly",
      "uvicorn",
    ),
  ),
)

#: What a record is called that matches nothing above. The API is the widest thing
#: this project does, so an unrecognised logger lands there rather than vanishing.
DEFAULT_SUBSYSTEM = "api"

LOG_FILENAMES = {
  "api": "sawa9ly-api.log",
  "dashboard": "sawa9ly-dashboard.log",
  "cli": "sawa9ly-cli.log",
  "cron": "sawa9ly-cron.log",
  "telegram": "sawa9ly-telegram.log",
}

#: Kept as they are at INFO regardless of `LOG_LEVEL`, and why.
ALWAYS_INFO_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")

#: Passed to both `uvicorn.run` calls. uvicorn installs its own handlers over the
#: root logger unless told not to, which would leave every file empty. None is the
#: value that means "do not configure logging yourself".
UVICORN_LOG_CONFIG = None

# Field names that mean a value must never reach a log. Used as a fallback: if a
# line mentions one of these but no `key=value` could be found, something is still
# appended to say so rather than leaving the line looking untouched.
SECRET_WORDS = (
  "password", "passwd", "secret", "token", "cookie", "api_key", "apikey",
  "key_hash", "authorization", "credential", "sawa9ly_password",
)

# The value after any of these, in a rendered line, and nothing else.
#
# The obvious implementation — drop `record.args` and move on — is not enough,
# and quietly is worse than loudly. It only helps a caller who passed the secret
# as an argument: `logger.info("login %s", password)`. A caller who wrote
# `logger.info(f"login {password}")`, or who built the string with `%` before
# handing it over, has already interpolated the value into the message and there
# is no argument left to drop. Since both styles occur in practice, the value is
# redacted out of the finished line instead, which covers either.
SECRET_PATTERN = re.compile(
  r"((?:passwo?rd|secret|token|cookie|api[_-]?key|key[_-]?hash|authorization"
  r"|credential)s?[\"']?\s*[=:]\s*[\"']?)([^\s,;\"'}\)]+)",
  re.IGNORECASE,
)

REDACTED = "[redacted]"

TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


class Subsystems:
  """Which log a record belongs in, and where those logs are written.

  The routing table and the file names, looked up by name. Kept apart from
  `Logging` so that the answer to "where does this line go" can be had without
  setting anything up.
  """

  @classmethod
  def of(cls, name):
    """Which subsystem a logger name belongs to.

    Prefix match on a dot boundary, so `src.services.telegram` matches
    `src.services.telegram` and `src.services.telegram.something`, but not
    `src.services.telegramx` — an unrelated module that merely starts with the
    same letters should not be filed with it.
    """
    for subsystem, prefixes in SUBSYSTEMS:
      for prefix in prefixes:
        if name == prefix or name.startswith(prefix + "."):
          return subsystem

    return DEFAULT_SUBSYSTEM

  @classmethod
  def files(cls):
    """The per-subsystem log paths, as a subsystem -> Path mapping.

    Empty when `LOG_FILE` is set, because that one file replaces them.
    """
    if Config.log_file():
      return {}

    directory = Config.log_dir()

    return {name: directory / filename for name, filename in LOG_FILENAMES.items()}

  @classmethod
  def path(cls, subsystem):
    """Where one subsystem's log is, or None when it is not being written."""
    return cls.files().get(subsystem)


class SecretFilter(logging.Filter):
  """Redacts anything that looks like a credential.

    The value is stripped out of the *rendered* line, so it works whether the
    caller passed a secret as an argument or interpolated it into the message
    first. A redaction is appended when a secret field is mentioned even if no
    `key=value` pair could be found, so a line that is merely about a password
    still shows that something was redacted rather than looking untouched.

    A filter is consulted once per handler, and this project attaches six of them
    (one console, five files), so the result is marked on the record and computed
    only the first time. Without that, a redaction would be attempted per handler,
    and a record could reach one handler unredacted and the next redacted.
  """

  MARKER = "_sawa9ly_redacted"

  def filter(self, record):
    if getattr(record, self.MARKER, False):
      return True

    # getMessage() renders the arguments, so by here an argument-supplied secret
    # and a pre-formatted one look identical.
    message = record.getMessage()

    redacted, matches = SECRET_PATTERN.subn(rf"\1{REDACTED}", message)

    if matches:
      message = redacted
    elif any(word in message.lower() for word in SECRET_WORDS):
      message = f"{message} {REDACTED}"

    # Take over the record with its own rendered text and no arguments left, so
    # the formatter cannot interpolate the arguments a second time. This has to
    # happen even when nothing matched: a record whose `msg` still holds a
    # format string and whose `args` have been dropped would be written out
    # literally as "login failed for %s" with the name missing from it.
    record.msg = message
    record.args = ()
    setattr(record, self.MARKER, True)

    return True


class SubsystemFilter(logging.Filter):
  """Keeps only the records belonging to one subsystem.

  One of these per file, so the routing happens once per handler rather than
  being decided at each call site. `SecretFilter` is added first on every handler
  so a record is redacted before anything can write it.
  """

  def __init__(self, subsystem):
    super().__init__()
    self.subsystem = subsystem

  def filter(self, record):
    return Subsystems.of(record.name) == self.subsystem


class SubsystemFileHandler(logging.FileHandler):
  """A file handler that makes its directory when it first writes.

  `delay=True` means the file itself is not created until something is logged,
  which is what keeps a quiet day from leaving empty files behind. It says nothing
  about the *directory*, though, and a missing parent directory turns the first
  log line into a `FileNotFoundError` from inside `emit` — which propagates out
  of `callHandlers` and takes the process with it. So the directory is made at
  the same moment, in the same place, that the file would have been.

  Created through `_open` because that is the point the stdlib opens the file, and
  overriding it rather than pre-creating directories at configure time is what
  keeps an untouched install free of empty log directories.
  """

  def _open(self):
    Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)

    return super()._open()


class JsonFormatter(logging.Formatter):
  """One JSON object per line, for a log collector."""

  def format(self, record):
    payload = {
      "time": self.formatTime(record),
      "level": record.levelname,
      "logger": record.name,
      "subsystem": Subsystems.of(record.name),
      "message": record.getMessage(),
    }

    if record.exc_info:
      payload["exception"] = self.formatException(record.exc_info)

    return json.dumps(payload, ensure_ascii=False)


class Logging:
  """The handlers on the root logger, and how they were arrived at."""

  @classmethod
  def formatter(cls):
    if Config.log_format() == "json":
      return JsonFormatter()

    return logging.Formatter(TEXT_FORMAT)

  @classmethod
  def _file_handler(cls, path, subsystem=None):
    """A handler writing to one file, redacting secrets before anything is written.

    `subsystem` None means every record belongs in this file, which is the case
    for the single-file override.
    """
    handler = SubsystemFileHandler(path, encoding="utf-8", delay=True)
    handler.setFormatter(cls.formatter())

    # Redaction first. A record that reached this handler's filter already
    # redacted is marked and passes through, so the order cannot leak a value into
    # a file that the console has not yet seen.
    handler.addFilter(SecretFilter())

    if subsystem is not None:
      handler.addFilter(SubsystemFilter(subsystem))

    return handler

  @classmethod
  def _console_handler(cls):
    # Unfiltered by subsystem: stderr is where a person is looking, and silently
    # dropping lines from it because a logger was named oddly would be worse than
    # a noisy terminal.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(cls.formatter())
    handler.addFilter(SecretFilter())

    return handler

  @classmethod
  def _pin_access_log(cls):
    """Hold the HTTP access log at INFO whatever `LOG_LEVEL` says.

    An api log that has stopped recording who called what is not an api log, and
    raising the level to quiet an application's own debugging should not delete
    the traffic history along with it. Only these three are pinned; the project's
    own loggers obey `LOG_LEVEL` as configured.
    """
    for name in ALWAYS_INFO_LOGGERS:
      logging.getLogger(name).setLevel(logging.INFO)

  @classmethod
  def configure(cls):
    """Set up the root logger: one console, plus one file per subsystem.

    Safe to call more than once — handlers are replaced rather than added, so a
    reload does not double every line. Returns the root logger.
    """
    handlers = [cls._console_handler()]

    single = Config.log_file()

    if single:
      handlers.append(cls._file_handler(single))
    else:
      for subsystem, path in Subsystems.files().items():
        handlers.append(cls._file_handler(path, subsystem))

    root = logging.getLogger()
    root.setLevel(Config.log_level())

    for existing in list(root.handlers):
      root.removeHandler(existing)

    for handler in handlers:
      root.addHandler(handler)

    cls._pin_access_log()

    return root

  @classmethod
  def describe(cls):
    """What logging is currently doing, for a status command."""
    files = Subsystems.files()

    return {
      "level": Config.log_level(),
      "format": Config.log_format(),
      "console": "stderr",
      # Only one of these is ever set: the single file replaces the directory, so
      # reporting both at once would describe a configuration that cannot happen.
      "single_file": str(Config.log_file()) if Config.log_file() else None,
      "directory": str(Config.log_dir()) if files else None,
      "files": {name: str(path) for name, path in files.items()},
    }
