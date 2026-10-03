"""Wilaya entity: one of Algeria's 58 provinces, under the site's own id."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Wilaya(Base):
  """A province, and the root the delivery reference data hangs off.

  `id` is **the site's wilaya id**, not one of ours. That is deliberate and it is
  the reason this table exists: the checkout form wants a number, the site's own
  dropdowns use that numbering, and every other table that names a wilaya — the
  communes, the delivery prices, a saved recipient — refers to it. Giving the
  table its own autoincrement key and keeping the site's beside it is the mistake
  this project already made once with products; see `database.md`.

  So there is no separate primary key. `id` is both, and a wilaya is created by
  seeding `src/seeds/wilayas_communes.sql`, never by the application.

  `number` is the zero-padded form the site prints next to the name (`01`), kept
  so a row can be matched against what is on screen. It is not a second key and
  nothing looks a row up by it.
  """

  __tablename__ = "wilayas"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String(128))
  number: Mapped[str | None] = mapped_column(String(8), default=None)
  # `server_default` as well as the Python default because these rows are written by
  # the seed file, and a raw INSERT does not run Python. Without it the load fails on
  # a NOT NULL it cannot see a value for.
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=utcnow, server_default=func.now(),
  )

  # No cascade on either side. A wilaya is reference data the site's own form
  # depends on, so removing one would orphan every commune and price pointing at
  # it, and nothing in the application deletes a wilaya at all.
  communes: Mapped[list["Commune"]] = relationship(back_populates="wilaya")
  delivery_prices: Mapped[list["DeliveryPrice"]] = relationship(back_populates="wilaya")

  @classmethod
  def get(cls, db, wilaya_id):
    """One wilaya by the site's id, or None."""
    return db.get(cls, int(wilaya_id))

  @classmethod
  def all(cls, db):
    """Every wilaya, in the site's own order, which is also alphabetical-ish.

    Ordered by `id` rather than by name so the list matches the numbering the
    site and the checkout form both use. Sorting by name would be a different
    list, not a better one.
    """
    return list(db.execute(select(cls).order_by(cls.id)).scalars())

  def as_dict(self):
    return {
      'id': self.id,
      'name': self.name,
      'number': self.number,
    }

  def __repr__(self):
    return f"<Wilaya {self.number or self.id} {self.name!r}>"