"""Order entity: a customer's basket being built, then placed."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class OrderState:
  """The states an order moves through.

  draft     - being built; lines may be added, removed and edited
  confirmed - posted to the website; no longer editable
  done      - finished with
  """

  DRAFT = "draft"
  CONFIRMED = "confirmed"
  DONE = "done"

  ALL = (DRAFT, CONFIRMED, DONE)
  EDITABLE = (DRAFT,)
  TRANSITIONS = {
    DRAFT: (CONFIRMED,),
    CONFIRMED: (DONE,),
    DONE: (),
  }

  @staticmethod
  def is_valid(state):
    return state in OrderState.ALL

  @staticmethod
  def can_transition(current, target):
    return target in OrderState.TRANSITIONS.get(current, ())


class Order(Base):
  """An order, made of order lines and addressed to a client."""

  __tablename__ = "orders"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  client_id: Mapped[int | None] = mapped_column(
    ForeignKey("clients.id", ondelete="SET NULL"), default=None, index=True
  )
  state: Mapped[str] = mapped_column(String(16), default=OrderState.DRAFT, index=True)
  # The reference the website returns once the order is submitted.
  reference: Mapped[str | None] = mapped_column(String(128), default=None)
  note: Mapped[str | None] = mapped_column(Text, default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

  user: Mapped["User"] = relationship(back_populates="orders")
  client: Mapped["Client"] = relationship(back_populates="orders")
  lines: Mapped[list["OrderLine"]] = relationship(
    back_populates="order", cascade="all, delete-orphan", lazy="selectin",
  )

  @classmethod
  def get(cls, db, order_id):
    return db.get(cls, int(order_id))

  @classmethod
  def all(cls, db, user_id=None, state=None):
    query = select(cls).order_by(cls.id.desc())
    if user_id is not None:
      query = query.where(cls.user_id == user_id)
    if state is not None:
      query = query.where(cls.state == state)
    return list(db.execute(query).scalars())

  @classmethod
  def create(cls, db, user_id, client_id=None, note=None):
    """Start a new draft order."""
    order = cls(user_id=user_id, client_id=client_id, note=note, state=OrderState.DRAFT)
    db.add(order)
    db.commit()
    return order

  def is_editable(self):
    """Whether lines may still be changed (draft only)."""
    return self.state in OrderState.EDITABLE

  def transition(self, db, target):
    """Move to another state, refusing transitions the machine disallows."""
    if not OrderState.is_valid(target):
      raise ValueError(f"Unknown order state: {target!r}")

    if target == self.state:
      return self

    if not OrderState.can_transition(self.state, target):
      allowed = ", ".join(OrderState.TRANSITIONS.get(self.state, ())) or "nothing"
      raise ValueError(
        f"Cannot move an order from {self.state!r} to {target!r} (allowed: {allowed})"
      )

    self.state = target
    db.commit()
    return self

  def total(self):
    """Sum of every line's quantity * price."""
    return sum(line.subtotal() for line in self.lines)

  def as_dict(self):
    return {
      'id': self.id,
      'state': self.state,
      'client_id': self.client_id,
      'reference': self.reference,
      'note': self.note,
      'total': self.total(),
      'lines': [line.as_dict() for line in self.lines],
      'created_at': str(self.created_at),
    }

  def __repr__(self):
    return f"<Order {self.id} {self.state}>"
