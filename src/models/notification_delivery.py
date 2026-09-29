"""NotificationDelivery entity: one person hearing about one event.

The fan-out half of a notification, in its own file because it is its own thing:
it answers "has this person been told yet", which is a different question from
"what happened" and outlives it — a delivery that failed stays failed, and the
product the event was about can be deleted without taking the event or the
record of who was told with it.

Carrying the outcome per person is what makes retry safe. With one `sent_at` on
the event, a single blocked chat would make the whole send look failed, and
retrying it would resend to everybody who already received it.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow

#: Why a delivery is recorded without having gone anywhere. Distinct from an
#: error, because nothing failed: there was simply nowhere to send it.
NO_CHAT = "no Telegram chat is linked to this account"


class NotificationDelivery(Base):
  """One person's copy of one notification, and whether it arrived."""

  __tablename__ = "notification_deliveries"
  # One row per person per event. This is the constraint that makes a repeat
  # impossible rather than merely unlikely, so two watches on one product cannot
  # become two messages.
  __table_args__ = (
    UniqueConstraint("notification_id", "user_id", name="uq_delivery_notification_user"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  notification_id: Mapped[int] = mapped_column(
    ForeignKey("notifications.id", ondelete="CASCADE"), index=True
  )
  user_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"), index=True
  )
  # Where it was aimed, kept even when it did not get there: the first question
  # about a failed send is which chat refused.
  chat_id: Mapped[str | None] = mapped_column(String(64), default=None)
  sent_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
  send_error: Mapped[str | None] = mapped_column(String(255), default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  notification: Mapped["Notification"] = relationship(back_populates="deliveries")
  user: Mapped["User"] = relationship()

  # --- sending --------------------------------------------------------

  def deliver(self, db, bot=None):
    """Try to send this copy. Returns True if it went.

    Never raises. A delivery that cannot be made is recorded and returns False,
    because the thing that noticed the event — the queue — must not fail for a
    reason that has nothing to do with the product.

    A user with no linked chat is recorded with `NO_CHAT` and is not retried by
    `undelivered`: there was no intent to notify them at the time, so the row is
    a record rather than a message waiting its turn.
    """
    from src.models import TelegramBinding
    from src.utils import Telegram, TelegramError

    binding = TelegramBinding.for_user(db, self.user_id)

    if binding is None or not binding.is_bound():
      self.send_error = NO_CHAT
      db.commit()
      return False

    self.chat_id = binding.chat_id

    try:
      (bot or Telegram()).send(
        binding.chat_id, self.notification.body
      )
    except TelegramError as error:
      self.send_error = str(error)[:255]
      db.commit()
      return False

    self.sent_at = utcnow()
    self.send_error = None
    db.commit()

    return True

  # --- lookups --------------------------------------------------------

  @classmethod
  def undelivered(cls, db, retryable=True):
    """Everything recorded and not yet sent, oldest first.

    `retryable` excludes the ones that were never a queued message: a delivery
    that found no linked chat was not held back by a failure, it had nowhere to
    go because the user had not opted in. Sending it an hour later is not
    delivering news, it is inventing it. `False` gives the full list, which is
    what an operator reading the table wants.
    """
    query = select(cls).where(cls.sent_at.is_(None)).order_by(cls.id)

    if retryable:
      query = query.where(cls.send_error != NO_CHAT)

    return list(db.execute(query).scalars())

  @classmethod
  def for_user(cls, db, user_id, limit=50):
    """One person's notifications, newest first."""
    return list(db.execute(
      select(cls)
      .where(cls.user_id == int(user_id))
      .order_by(cls.id.desc())
      .limit(limit)
    ).scalars())

  @property
  def delivered(self):
    return self.sent_at is not None

  def as_dict(self):
    return {
      'id': self.id,
      'notification_id': self.notification_id,
      'user_id': self.user_id,
      'chat_id': self.chat_id,
      'sent_at': str(self.sent_at) if self.sent_at else None,
      'send_error': self.send_error,
      'delivered': self.delivered,
      'created_at': str(self.created_at),
    }

  def __repr__(self):
    return (
      f"<NotificationDelivery #{self.id} notification={self.notification_id} "
      f"user={self.user_id} sent={self.delivered}>"
    )
