"""Shared helpers for the command line."""

import json

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
