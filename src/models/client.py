"""Client entity: a delivery recipient belonging to a user."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Client(Base):
  """Somebody an order is shipped to.

  Holds the fields the site's checkout form asks for, so an order can be
  submitted without retyping them.

  There is deliberately **no `note`**. A note belongs to the thing it is about, and
  the two things that carry one — an order and a line on it — already do. On a
  recipient it had nowhere to be shown and nothing to distinguish it from the
  order's own note, so it was a field that could be written and never read.
  """

  __tablename__ = "clients"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  full_name: Mapped[str] = mapped_column(String(255))
  phone: Mapped[str | None] = mapped_column(String(64), default=None)
  adresse: Mapped[str | None] = mapped_column(Text, default=None)
  wilaya_id: Mapped[int | None] = mapped_column(Integer, default=None)
  commune_id: Mapped[int | None] = mapped_column(Integer, default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  user: Mapped["User"] = relationship(back_populates="clients")
  orders: Mapped[list["Order"]] = relationship(back_populates="client")

  @classmethod
  def get(cls, db, client_id):
    return db.get(cls, int(client_id))

  @classmethod
  def all(cls, db, user_id, limit=None, offset=None, search=None):
    """Every delivery recipient of one user, optionally narrowed and paged.

    `search` matches the name or the phone number: those are the two things
    somebody looking for a recipient knows.
    """
    from src.models.paging import Paging

    return list(db.execute(
      Paging.apply(cls._filtered(user_id, search), limit, offset)
    ).scalars())

  @classmethod
  def page(cls, db, user_id, limit=None, offset=None, search=None):
    """One page of a user's delivery recipients, and the total before paging.

    Separate from `all` because `all` is what the CLI reads and it keeps
    returning a plain list. Only the HTTP list route needs the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(user_id, search), limit, offset)

  @classmethod
  def _filtered(cls, user_id, search=None):
    """The select every list of a user's clients shares."""
    from src.utils.search import Search

    query = select(cls).where(cls.user_id == user_id).order_by(cls.full_name)

    match = Search.match(
      Search.like(cls.full_name, search),
      Search.like(cls.phone, search),
    )

    if match is not None:
      query = query.where(match)

    return query

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
    """This client as the checkout form expects it.

    `note` is not here even though the site's form has one. Nothing writes it
    from a client any more, and an absent key is simply not pushed — so the form
    field keeps the site's own default rather than being told to clear it.
    """
    return {
      'full_name': self.full_name,
      'phone': self.phone,
      'adresse': self.adresse,
      'wilaya_id': self.wilaya_id,
      'commune_id': self.commune_id,
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
    }

  def __repr__(self):
    return f"<Client {self.full_name!r}>"
