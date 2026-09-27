"""Which entities a user wants kept up to date.

A tracker is a subscription, not a job. It says "this user cares about this
thing"; the queue in `src/services/tracking.py` decides what to actually scrape,
and it collapses many trackers for the same target into one scan.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base, utcnow


class TargetModel:
  """The kinds of thing that can be tracked.

  Only the entity names the queue knows how to refresh. It is a string rather
  than a foreign key because the target is polymorphic: one column pair points
  at whichever table the name refers to.
  """

  PRODUCT = "Product"

  ALL = (PRODUCT,)

  @staticmethod
  def is_valid(name):
    return name in TargetModel.ALL


class Tracker(Base):
  """One user's interest in one target.

  `target_id` is the target's own primary key in its own table — for a product
  that is the internal `products.id`, not the sawa9ly id, because the row is
  what gets cascaded away when the catalogue entry is deleted. The queue
  resolves it to the sawa9ly id before scraping.

  The unique constraint is per (target, user) rather than per target, because
  several users may watch the same product. The queue scans that product once
  and stamps every tracker on it, so the number of watchers does not change the
  number of requests made to the site.
  """

  __tablename__ = "trackers"
  __table_args__ = (
    UniqueConstraint("target_model", "target_id", "user_id", name="uq_tracker_target_user"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  target_model: Mapped[str] = mapped_column(String(64), index=True)
  target_id: Mapped[int] = mapped_column(Integer, index=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  # Per tracker rather than per target, so each row answers "when was this last
  # verified for the person who asked" without a second table.
  last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
  last_changed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

  # --- lookups ------------------------------------------------------

  @classmethod
  def for_user(cls, db, user_id, target_model=None):
    """A user's trackers, optionally only for one kind of target."""
    query = select(cls).order_by(cls.target_model, cls.target_id)

    if target_model is not None:
      query = query.where(cls.target_model == target_model)

    return list(db.execute(query.where(cls.user_id == user_id)).scalars())

  @classmethod
  def get(cls, db, tracker_id):
    return db.get(cls, tracker_id)

  @classmethod
  def find(cls, db, user_id, target_model, target_id):
    """The one tracker a user has for a target, or None."""
    return db.execute(
      select(cls).where(
        cls.user_id == user_id,
        cls.target_model == target_model,
        cls.target_id == target_id,
      )
    ).scalar_one_or_none()

  @classmethod
  def watch(cls, db, user_id, target_model, target_id):
    """Start tracking, returning (tracker, created).

    Watching something already watched is not an error: it returns the existing
    row so a repeated command is harmless.
    """
    existing = cls.find(db, user_id, target_model, target_id)

    if existing is not None:
      return existing, False

    tracker = cls(user_id=user_id, target_model=target_model, target_id=target_id)
    db.add(tracker)
    db.commit()

    return tracker, True

  @classmethod
  def unwatch(cls, db, user_id, target_model, target_id):
    """Stop tracking. True if a tracker was removed."""
    tracker = cls.find(db, user_id, target_model, target_id)

    if tracker is None:
      return False

    db.delete(tracker)
    db.commit()

    return True

  @classmethod
  def watched_targets(cls, db, target_model=None):
    """Every distinct target that at least one user is tracking.

    This is the deduplication: the queue scrapes each of these once, however
    many tracker rows point at it. A target nobody watches is simply not in the
    list, which is what keeps the queue off untracked products entirely.
    """
    query = select(
      cls.target_model, cls.target_id, cls.id
    ).order_by(cls.target_model, cls.target_id)

    if target_model is not None:
      query = query.where(cls.target_model == target_model)

    rows = db.execute(query).all()
    seen = []
    known = set()

    for target_model, target_id, tracker_id in rows:
      key = (target_model, target_id)

      if key in known:
        continue

      known.add(key)
      seen.append({'target_model': target_model, 'target_id': target_id})

    return seen

  @classmethod
  def trackers_for(cls, db, target_model, target_id):
    """Every tracker pointing at one target, for stamping after a scan."""
    return list(db.execute(
      select(cls).where(
        cls.target_model == target_model, cls.target_id == target_id
      )
    ).scalars())

  def as_dict(self):
    return {
      'id': self.id,
      'user_id': self.user_id,
      'target_model': self.target_model,
      'target_id': self.target_id,
      'created_at': str(self.created_at) if self.created_at else None,
      'last_checked_at': str(self.last_checked_at) if self.last_checked_at else None,
      'last_changed_at': str(self.last_changed_at) if self.last_changed_at else None,
    }

  def __repr__(self):
    return f"<Tracker {self.target_model}#{self.target_id} user={self.user_id}>"
