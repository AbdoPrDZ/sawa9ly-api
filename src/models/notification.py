"""Notification entity: one thing that happened, worth telling people about.

A notification is a **record of an event**, not a call. It holds no recipient: one
availability change is one row however many people are watching that product, and
the fan-out lives in `NotificationDelivery`, one row per person. That split is what
stops the same event being written once per watcher, and it is what lets a send
that failed for one person be retried without resending to everybody it already
reached.

So a Notification answers *what happened*; a delivery answers *who has been told
yet*. Writing the row is the sending — `create` does both — because a message that
was never recorded cannot be accounted for, and a row that was recorded but never
sent is one nobody looks at.

`body` is the text that went, verbatim, and it is the audit trail. That is also
why the product is a `SET NULL` foreign key rather than a hard dependency: the
message stays readable after the product is deleted, which is the right outcome
for a record of something somebody was told.
"""

from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Notification(Base):
  """One event, and nothing about who has heard about it."""

  #: What an event was about. Plain strings rather than an enum, because the set
  #: will grow and an unfamiliar value in `kind` is better than a migration every
  #: time somebody adds a second one.
  #:
  #: One kind for "a watched product changed", not one per field: a scrape that
  #: finds both the price and the stock different is one event that happened
  #: once. Which fields moved is in `body`, where a reader wants it.
  KIND_PRODUCT_CHANGED = "product.changed"

  #: How long an undelivered notification stays worth retrying. Long enough to
  #: cover somebody unblocking their bot over lunch, short enough that the message
  #: has not gone stale in the meantime.
  RETRY_WITHIN_SECONDS = 3600

  __tablename__ = "notifications"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  kind: Mapped[str] = mapped_column(String(48), index=True)
  product_id: Mapped[int | None] = mapped_column(
    ForeignKey("products.id", ondelete="SET NULL"), default=None, index=True
  )
  title: Mapped[str] = mapped_column(String(255))
  body: Mapped[str] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  product: Mapped["Product | None"] = relationship(back_populates="notifications")
  deliveries: Mapped[list["NotificationDelivery"]] = relationship(
    back_populates="notification", cascade="all, delete-orphan", lazy="selectin",
  )

  # --- creating one, which is how one is sent -------------------------

  @classmethod
  def create(cls, db, kind, title, body, user_ids, product_id=None, bot=None):
    """Record an event and tell everyone in `user_ids` about it.

    The recipients are deduplicated here rather than by the caller, because two
    watches on one product are one fact and must not become two messages — and
    forgetting to dedupe is a bug that shows up as spam, not as an error.

    Never raises for a delivery problem. A refused message is a delivery row with
    `send_error` set, and the event still stands: the product went out of stock
    whatever Telegram thinks about it.
    """
    row = cls(kind=kind, title=title, body=body, product_id=product_id)
    db.add(row)
    db.commit()

    row.send_to(db, user_ids, bot)

    return row

  def send_to(self, db, user_ids, bot=None):
    """Give each of `user_ids` a delivery, and try to send it.

    Idempotent per person: somebody who already has a delivery for this event is
    skipped, so a second call does not duplicate what the first already sent.
    """
    from src.models import NotificationDelivery

    already = {delivery.user_id for delivery in self.deliveries}

    for user_id in dict.fromkeys(int(u) for u in user_ids):
      if user_id in already:
        continue

      delivery = NotificationDelivery(notification_id=self.id, user_id=user_id)
      db.add(delivery)

      # Flush so `delivery.notification` resolves, but do not commit per row: one
      # commit for the whole fan-out, and the sends happen between.
      db.flush()

      delivery.deliver(db, bot)

    # `deliveries` was loaded empty when this row was inserted, so without this
    # it would still read empty afterwards and `sent` and `undelivered` would
    # report nothing. The caller counts from the row, so it has to be right.
    db.expire(self, ["deliveries"])

    return self

  @classmethod
  def retry_pending(cls, db, bot=None, within_seconds=None):
    """Try again the deliveries of recent events that have not gone out.

    Separate from `create` on purpose. A chat that was blocked for an hour must
    not produce an hour of identical messages the moment it works again — so a
    failure is retried when somebody asks, not as a side effect of the next scan.

    **Bounded twice**, and both bounds matter. By age, because a notification
    says what was true when it was noticed and stock goes back in stock — telling
    somebody now that a product went out of stock three days ago is worse than
    telling them nothing, because it is confidently wrong. And by *why* it failed:
    a delivery that found no linked chat is not retried at all, because the user
    had not opted in when the event happened, and a message from an hour ago is
    not news they asked for. Only a chat that was there and refused is retried.
    """
    from src.db import as_utc, utcnow
    from src.models import NotificationDelivery

    window = cls.RETRY_WITHIN_SECONDS if within_seconds is None else within_seconds
    cutoff = utcnow() - timedelta(seconds=window)

    retried = 0

    for delivery in NotificationDelivery.undelivered(db):
      if delivery.notification is None:
        continue

      if as_utc(delivery.notification.created_at) < cutoff:
        continue

      if delivery.deliver(db, bot):
        retried += 1

    return retried

  # --- lookups --------------------------------------------------------

  @classmethod
  def for_user(cls, db, user_id, limit=50):
    """The events one user has been told about, newest first."""
    from src.models import NotificationDelivery

    return list(db.execute(
      select(cls)
      .join(NotificationDelivery, NotificationDelivery.notification_id == cls.id)
      .where(NotificationDelivery.user_id == int(user_id))
      .order_by(cls.id.desc())
      .limit(limit)
    ).scalars())

  @classmethod
  def latest_for(cls, db, kind, product_id, limit=1):
    """The most recent events of one kind about one product.

    Deduplication reads from here rather than from a flag on the row, so "has this
      already been said" is answered by the history rather than by a field that
      can disagree with it.
    """
    return list(db.execute(
      select(cls)
      .where(cls.kind == kind)
      .order_by(cls.id.desc())
      .limit(limit)
    ).scalars())

  # --- shape ----------------------------------------------------------

  @property
  def sent(self):
    """How many people have actually received it."""
    return sum(1 for d in self.deliveries if d.sent_at is not None)

  @property
  def undelivered(self):
    return [d for d in self.deliveries if d.sent_at is None]

  def as_dict(self):
    return {
      'id': self.id,
      'kind': self.kind,
      'product_id': self.product.product_id if self.product else self.product_id,
      'title': self.title,
      'body': self.body,
      'created_at': str(self.created_at),
      'recipients': len(self.deliveries),
      'sent': self.sent,
    }

  def __repr__(self):
    # Never the body: it is long, and a repr ends up in logs.
    return f"<Notification #{self.id} {self.kind} sent={self.sent}/{len(self.deliveries)}>"
