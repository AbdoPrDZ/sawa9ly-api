"""Shared helpers for the command line."""

import errno
import json
import socket
import sys

from src.db import session_scope
from src.utils.livewire import ensure_db


class Cli:
  """Small utilities every command group needs."""

  @staticmethod
  def db():
    """An open database session, with the tables created."""
    ensure_db()
    return session_scope()

  @staticmethod
  def assert_port_free(host, port, flag="--port"):
    """Exit with an actionable message if something already holds this port.

    A pre-flight check, run before the server starts rather than as an
    `except` around it, because the alternative is the failure this replaces: a
    `uvicorn` traceback about `OSError: [Errno 10048]` arriving *after* a banner
    twenty lines long, which says neither what is wrong nor what to do about it.

    It binds and immediately closes, which is a check and not a reservation — a
    port free now can be taken a moment later, and `uvicorn` still has to lose
    that race on its own. What it buys is that the common case fails with a
    sentence instead of an errno.

    Only `EADDRINUSE` and `EACCES` are handled, because those are the two that
    have a thing a person can do: stop the other process, or choose another port.
    Anything else is left to propagate.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
      probe.bind((host, port))
    except OSError as error:
      if error.errno == errno.EADDRINUSE:
        raise SystemExit(
          f"error: {host}:{port} is already in use, so the server cannot bind.\n"
          f"  Another copy of this server may already be running, or something "
          f"else has taken the port.\n"
          f"  Find the holder with: {Cli._holder_command(port)}\n"
          f"  Or choose another port: {flag} <number>"
        ) from None

      if error.errno == errno.EACCES:
        raise SystemExit(
          f"error: {host}:{port} needs a privilege this process does not have.\n"
          f"  Ports below 1024 are reserved; pick one above it with: {flag} <number>"
        ) from None

      raise
    finally:
      probe.close()

  @staticmethod
  def _holder_command(port):
    """The command that names whatever is holding a port, per platform.

    Windows calls this `netstat`, and its output has to be filtered by hand
    because it lists every connection on the machine; the two `findstr` variants
    narrow it to a listening socket and to the process id respectively.
    """
    if sys.platform == "win32":
      return f'netstat -ano | findstr "LISTENING" | findstr ":{port}"'

    return f"lsof -i tcp:{port} -sTCP:LISTEN"

  @staticmethod
  def super_username():
    """The super admin, used when `--user` is omitted.

    Resolved from the database rather than the environment, because the database
    is what actually holds the account: a `super` created by hand and one
    bootstrapped from `SUPER_ADMIN_USERNAME` are equally real, and the app refuses
    to start without one either way.

    An installation with several supers is **refused** rather than guessed at.
    Picking the first would make a command act for whichever account happened to
    be created earliest, which is exactly the silent-wrong-account problem the
    original "no default" rule existed to prevent. `SUPER_ADMIN_USERNAME` breaks
    the tie when it names one of them.
    """
    from src.config import Config
    from src.models import Role, User

    with Cli.db() as db:
      supers = (
        db.query(User).filter(User.role == Role.SUPER).order_by(User.id).all()
      )

    if not supers:
      raise SystemExit(
        "error: no --user given and there is no 'super' account. Create one with: "
        f"python main.py user add <name> --role {Role.SUPER} --login-password <password>"
      )

    configured = Config.super_username()

    if configured:
      for user in supers:
        if user.username == configured:
          return user.username

    if len(supers) == 1:
      return supers[0].username

    names = ", ".join(user.username for user in supers)
    raise SystemExit(
      f"error: no --user given and there are {len(supers)} super accounts ({names}). "
      f"Pass --user to say which, or set {Config.SUPER_ADMIN_USERNAME_VAR}."
    )

  @staticmethod
  def username(username=None):
    """The account a command acts for: the one named, or the super admin."""
    return username or Cli.super_username()

  @staticmethod
  def user(db, username):
    """Look up a user or exit with a clear message."""
    from src.models import User

    name = Cli.username(username)
    user = User.get(db, name)

    if user is None:
      raise SystemExit(f"error: no user named '{name}'")

    return user

  @staticmethod
  def json_map(value, flag):
    """Parse a JSON object argument, exiting with a clear message."""
    try:
      parsed = json.loads(value)
    except ValueError:
      raise SystemExit(f"{flag} must be JSON, got {value!r}")

    if not isinstance(parsed, dict):
      raise SystemExit(f"{flag} must be a JSON object, got {value!r}")

    return parsed

  @staticmethod
  def product_id_of(args):
    """The product id from the command line.

    There is no environment fallback: a command that acts on a product has to
    name one. A default taken from the environment would quietly operate on
    whatever was last configured, which is how the wrong product gets ordered.
    """
    product_id = getattr(args, 'product_id', None)

    if not product_id:
      raise SystemExit(
        "a product id is required, e.g. python main.py cart add 5663"
      )

    return product_id

  @staticmethod
  def livewire(user):
    """A Livewire client for the named user, or the super admin.

    Built per command rather than shared: a CLI run is one short-lived process
    acting for one explicitly named account.
    """
    from src.utils import Livewire

    return Livewire(Cli.username(user))
