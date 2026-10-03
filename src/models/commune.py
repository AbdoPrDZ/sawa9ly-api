"""Commune entity: a town or district, under the site's own id."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Commune(Base):
  """A commune, belonging to exactly one wilaya.

  `id` is **the site's commune id**, for the same reason `Wilaya.id` is the site's
  wilaya id: the checkout form is sent a number and that number is this one. The
  site has no commune list page and no search, so the pairing between a commune
  and its wilaya is not something this project can read off a page — it comes
  from `src/seeds/wilayas_communes.sql`, which is generated once from the site's
  own commune select plus a commune-to-wilaya listing.

  `name` is the site's own Arabic spelling, kept verbatim. There is no Latin
  transliteration column: producing one means guessing between several
  established spellings of the same toponym, and a guessed column is a second
  answer to "what is this place called" that nobody can check.
  """

  __tablename__ = "communes"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  # Indexed because the only question ever asked of this table is "the communes of
  # this wilaya", which is what a cascading dropdown asks on every change.
  wilaya_id: Mapped[int] = mapped_column(
    ForeignKey("wilayas.id"), index=True,
  )
  name: Mapped[str] = mapped_column(String(128))
  # `server_default` as well as the Python default because these rows come from the
  # seed file, and a raw INSERT does not run Python.
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=utcnow, server_default=func.now(),
  )

  # No cascade. A commune is reference data the site's form depends on; deleting
  # one would leave a recipient pointing at a number that means nothing.
  wilaya: Mapped["Wilaya"] = relationship(back_populates="communes")

  @classmethod
  def get(cls, db, commune_id):
    """One commune by the site's id, or None."""
    return db.get(cls, int(commune_id))

  @classmethod
  def all(cls, db, wilaya_id=None):
    """Every commune, or only one wilaya's, ordered by the site's id.

    Ordered by `id` because that is the order the site's own select lists them in,
    which is what somebody comparing the dropdown against the site expects.
    """
    query = select(cls)

    if wilaya_id is not None:
      query = query.where(cls.wilaya_id == int(wilaya_id))

    return list(db.execute(query.order_by(cls.id)).scalars())

  def as_dict(self):
    return {
      'id': self.id,
      'wilaya_id': self.wilaya_id,
      'name': self.name,
    }

  def __repr__(self):
    return f"<Commune {self.id} {self.name!r}>"