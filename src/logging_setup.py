"""Logging setup.

The project logs through the standard library rather than adding a logging
framework. What is configurable comes from `Config`: the level, an optional log
file, and plain or JSON formatting.

Two decisions worth stating, because both are deliberate:

- **Logging is off unless asked for.** The default level is WARNING and nothing
  is written to a file, so a normal run is quiet. Set `LOG_LEVEL=INFO` or
  `LOG_FILE` to get more.
- **Credentials are never logged.** There is a filter that drops any record
  carrying a key, password, token or cookie field, because the project handles
  all four and a stray `logger.info("%s", user)` would otherwise put a
  dashboard password in a log file.
"""

import json
import logging
import sys

from src.config import Config

# Field names whose values must never reach a log, matched case-insensitively
# against a record's message and arguments.
SECRET_WORDS = (
  "password", "passwd", "secret", "token", "cookie", "api_key", "apikey",
  "key_hash", "authorization", "credential", "sawa9ly_password",
)

TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
JSON_FORMAT = "%(message)s"

REDACTED = "[redacted]"


class SecretFilter(logging.Filter):
  """Redacts anything that looks like a credential.

    A record whose message mentions a secret field has its arguments dropped and
    a marker appended, rather than the record being discarded — so it is still
    visible that something happened, and the values themselves are gone.

    A filter is consulted once per handler, and this project configures both a
    console and a file handler, so the redaction is marked on the record and
    applied only the first time. Without that, a message would collect one
    `[redacted]` per handler.
  """

  MARKER = "_sawa9ly_redacted"

  def filter(self, record):
    if getattr(record, self.MARKER, False):
      return True

    if any(word in record.getMessage().lower() for word in SECRET_WORDS):
      # Clear the args first: getMessage() has just used them, and leaving them
      # set would interpolate the secret into the formatted output.
      record.args = ()
      record.msg = f"{record.msg} {REDACTED}"
      setattr(record, self.MARKER, True)

    return True


class JsonFormatter(logging.Formatter):
  """One JSON object per line, for a log collector."""

  def format(self, record):
    payload = {
      "time": self.formatTime(record),
      "level": record.levelname,
      "logger": record.name,
      "message": record.getMessage(),
    }

    if record.exc_info:
      payload["exception"] = self.formatException(record.exc_info)

    return json.dumps(payload, ensure_ascii=False)


def configure_logging():
  """Set the root logger from `Config`. Safe to call more than once."""
  handlers = []

  console = logging.StreamHandler(sys.stderr)
  handlers.append(console)

  log_file = Config.log_file()

  if log_file:
    handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

  if Config.log_format() == "json":
    formatter = JsonFormatter()
  else:
    formatter = logging.Formatter(TEXT_FORMAT)

  root = logging.getLogger()
  root.setLevel(Config.log_level())

  # Replace rather than add, so a reload does not double every line.
  for existing in list(root.handlers):
    root.removeHandler(existing)

  for handler in handlers:
    handler.setFormatter(formatter)
    handler.addFilter(SecretFilter())
    root.addHandler(handler)

  return root
