"""Watching products for changes, over HTTP.

The queue itself is not exposed as a route. Triggering a pass would let one web
request fan out into hundreds of requests to the live site, which is the fastest
way to get blocked; that belongs to `python main.py cron`, on a schedule.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import TargetModel
from src.schemas import TrackerIn, TrackerOut, WatchedTrackerOut
from src.services import Tracking, TrackingError


class TrackersController:
  """A user's own watches."""

  router = APIRouter(prefix="/trackers", tags=["tracking"])

  @router.get("", response_model=list[TrackerOut])
  def list_trackers(target_model: str | None = None,
                    user=Depends(Dependencies.get_any_user),
                    db: Session = Depends(Dependencies.get_db)):
    """What this user is watching."""
    if target_model is not None and not TargetModel.is_valid(target_model):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown target '{target_model}'; expected one of "
               f"{', '.join(TargetModel.ALL)}.",
      )

    return Tracking.for_user(db, user.username, target_model)

  @router.post("", response_model=WatchedTrackerOut, status_code=status.HTTP_201_CREATED)
  def watch(body: TrackerIn, user=Depends(Dependencies.get_any_user),
            db: Session = Depends(Dependencies.get_db)):
    """Start watching a saved product.

    Watching something already watched returns 201 with `created: false` rather
    than a conflict, because the caller's intent — "keep this watched" — is
    already satisfied.
    """
    try:
      tracker, created = Tracking.watch_product(db, body.product_id, user.username)
    except TrackingError as error:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
      ) from error

    row = Tracking.describe(db, tracker)
    row['created'] = created

    return row

  @router.delete("", response_model=dict)
  def unwatch(body: TrackerIn, user=Depends(Dependencies.get_any_user),
              db: Session = Depends(Dependencies.get_db)):
    """Stop watching a product."""
    if not Tracking.unwatch_product(db, body.product_id, user.username):
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Not watching product {body.product_id}.",
      )

    return {"unwatched": body.product_id}
