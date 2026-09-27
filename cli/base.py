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
  def user(db, username):
    """Look up a user or exit with a clear message."""
    from src.models import User

    user = User.get(db, username)

    if user is None:
      raise SystemExit(f"error: no user named '{username}'")

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
        "a product id is required, e.g. python main.py cart-add 5663"
      )

    return product_id

  @staticmethod
  def livewire(user):
    """A Livewire client for the named user.

    Built per command rather than shared: a CLI run is one short-lived process
    acting for one explicitly named account.
    """
    from src.utils import Livewire

    return Livewire(user)
