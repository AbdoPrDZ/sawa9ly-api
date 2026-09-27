"""Client entity: a delivery recipient belonging to a user."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Client(Base):
  """Somebody an order is shipped to.

  Holds the fields the site's checkout form asks for, so an order can be
  submitted without retyping them.
  """

  __tablename__ = "clients"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  full_name: Mapped[str] = mapped_column(String(255))
  phone: Mapped[str | None] = mapped_column(String(64), default=None)
  adresse: Mapped[str | None] = mapped_column(Text, default=None)
  wilaya_id: Mapped[int | None] = mapped_column(Integer, default=None)
  commune_id: Mapped[int | None] = mapped_column(Integer, default=None)
  note: Mapped[str | None] = mapped_column(Text, default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  user: Mapped["User"] = relationship(back_populates="clients")
  orders: Mapped[list["Order"]] = relationship(back_populates="client")

  @classmethod
  def get(cls, db, client_id):
    return db.get(cls, int(client_id))

  @classmethod
  def all(cls, db, user_id):
    return list(db.execute(
      select(cls).where(cls.user_id == user_id).order_by(cls.full_name)
    ).scalars())

  @classmethod
  def get_or_create(cls, db, user_id, full_name, **fields):
    """Reuse a client with the same name for this user, else create one."""
    client = db.execute(
      select(cls).where(cls.user_id == user_id, cls.full_name == full_name)
    ).scalar_one_or_none()

    if client is None:
      client = cls(user_id=user_id, full_name=full_name, **fields)
      db.add(client)
    else:
      for key, value in fields.items():
        if value is not None:
          setattr(client, key, value)

    db.commit()
    return client

  def checkout_fields(self):
    """This client as the checkout form expects it."""
    return {
      'full_name': self.full_name,
      'phone': self.phone,
      'adresse': self.adresse,
      'wilaya_id': self.wilaya_id,
      'commune_id': self.commune_id,
      'note': self.note,
    }

  def as_dict(self):
    return {
      'id': self.id,
      'user_id': self.user_id,
      'full_name': self.full_name,
      'phone': self.phone,
      'adresse': self.adresse,
      'wilaya_id': self.wilaya_id,
      'commune_id': self.commune_id,
      'note': self.note,
    }

  def __repr__(self):
    return f"<Client {self.full_name!r}>"
