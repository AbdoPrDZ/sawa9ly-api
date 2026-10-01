"""Watching products for changes, as MCP tools.

The three operations the HTTP API exposes under `/api/v1/trackers`.

**When** a watch is checked is not here. Running the pass is `python main.py
cron`, on a schedule, and it is deliberately not a tool: one tool call would
otherwise fan out into hundreds of requests to the live site, which is the
fastest way to be blocked.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.models import TargetModel
from src.services import Tracking


class TrackersTools:
  """The caller's own watches."""

  @staticmethod
  def list_trackers(target_model: str = None):
    """What the caller is watching, with each target resolved for display.

    `target_model` narrows to one kind of target; leave it out for all of them.
    The only kind there is today is 'Product'.
    """
    if target_model is not None and not TargetModel.is_valid(target_model):
      raise McpError(
        f"Unknown target '{target_model}'; expected one of "
        f"{', '.join(TargetModel.ALL)}."
      )

    user = McpAuth.user()

    with session_scope() as db:
      return Tracking.for_user(db, user.username, target_model)

  @staticmethod
  def watch_product(product_id: int):
    """Start watching a saved product for changes to its price or availability.

    `product_id` is the sawa9ly id. The product must already be in the catalogue;
    there is nothing to diff against otherwise, so an unsaved id is an error
    rather than a watch on nothing.

    `created: false` in the answer means it was already being watched. That is
    not a failure — the intent, "keep this watched", is already satisfied.
    """
    user = McpAuth.user()

    with session_scope() as db:
      tracker, created = Tracking.watch_product(db, product_id, user.username)

      return {**Tracking.describe(db, tracker), "created": created}

  @staticmethod
  def unwatch_product(product_id: int):
    """Stop watching a product. Watching nothing is an error, not a no-op."""
    user = McpAuth.user()

    with session_scope() as db:
      if not Tracking.unwatch_product(db, product_id, user.username):
        raise McpError(
          f"{user.username} is not watching product {product_id}."
        )

      return {"unwatched": int(product_id), "user": user.username}

  @staticmethod
  def tools():
    return (
      TrackersTools.list_trackers,
      TrackersTools.watch_product,
      TrackersTools.unwatch_product,
    )
