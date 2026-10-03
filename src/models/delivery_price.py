"""DeliveryPrice entity: what it costs to ship one order to one wilaya."""

from datetime import datetime

from sqlalchemy import (
  Boolean,
  DateTime,
  ForeignKey,
  Integer,
  Numeric,
  select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class ReferenceDataMissing(RuntimeError):
  """Raised when the delivery reference data has not been loaded.

  Its own class rather than a `ValueError` because it is a setup step with a
  known fix, not a bad argument: the CLI reports it as `error: ...` with a
  non-zero exit and the controllers turn it into a 409, while a genuine fault
  stays a 502.
  """


class DeliveryPrice(Base):
  """The site's delivery prices for one wilaya, as of the last sync.

  Global, like the catalogue: the site publishes one price list for everybody,
  so there is no `user_id` here and the rows are not owned by whoever ran the
  sync.

  **`wilaya_id` is a foreign key to `wilayas.id`, and that id is the site's own.**
  It was a bare integer until the wilayas table existed. As a key it is what makes
  a price attachable to a name: the shipping page prints the wilaya's number and
  name but the scraper only ever reads the number, so without the table a saved
  price says `16` and nothing about who that is. The unique constraint is what
  the key already implied — a wilaya has at most one price — and it is kept
  explicitly because a re-sync has to update the row rather than add a second one.

  `price` and `office_price` are the two ways an order reaches the customer:
  delivered to the address, or collected from the carrier's office. Both are
  `Numeric`, not a formatted string, because these are the two numbers this table
  exists to hold; the site's own `'9,500 دج'` display text is parsed once on the
  way in and never stored.

  `available` is false where the site prints غير متوفر. That is a real, distinct
  answer — the wilaya is served but not by this price list, or not at all — and
  collapsing it into a null price would lose the difference between "no delivery
  here" and "we do not know the price". A row is kept either way, so a wilaya that
  *becomes* available is an update rather than an insert.
  """

  __tablename__ = "delivery_prices"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  # Unique so a re-sync updates the wilaya's row instead of adding a second one
  # for the same wilaya; without it every sync would double the table and a
  # lookup by wilaya would be ambiguous.
  wilaya_id: Mapped[int] = mapped_column(
    ForeignKey("wilayas.id"), unique=True, index=True,
  )
  available: Mapped[bool] = mapped_column(
    Boolean, default=True, server_default="1",
  )
  price: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
  office_price: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

  # No cascade either way. The wilaya is reference data the site's form needs, and
  # the price is the only record of what the site charged, so neither is a thing
  # to delete on the way to deleting something else.
  wilaya: Mapped["Wilaya"] = relationship(back_populates="delivery_prices")

  @classmethod
  def get(cls, db, wilaya_id):
    """The saved price for one wilaya, or None."""
    return db.execute(
      select(cls).where(cls.wilaya_id == int(wilaya_id))
    ).scalar_one_or_none()

  @classmethod
  def all(cls, db, available=None, limit=None, offset=None):
    """Every wilaya's saved price, ordered by wilaya.

    `available` narrows the list rather than defaulting to showing only
    deliverable wilayas: an unavailable one is the answer somebody checking
    coverage is looking for, and hiding it by default would make the table lie
    about what the site says.
    """
    from src.models.paging import Paging

    return list(db.execute(
      Paging.apply(cls._filtered(available), limit, offset)
    ).scalars())

  @classmethod
  def page(cls, db, available=None, limit=None, offset=None):
    """One page of saved prices, and the total before paging.

    Separate from `all` because `all` is what the CLI reads and it keeps
    returning a plain list. Only the HTTP list route needs the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(available), limit, offset)

  @classmethod
  def _filtered(cls, available=None):
    """The select every list of saved prices shares.

    One method because `all` and `page` must agree on what `available` narrows —
    two copies of a filter is how a list route ends up answering a question the
    CLI does not.
    """
    query = select(cls).order_by(cls.wilaya_id)

    if available is not None:
      query = query.where(cls.available == bool(available))

    return query

  @classmethod
  def sync(cls, db, rows):
    """Replace the saved prices with a fresh scrape.

    `rows` is what the shipping page yielded, one dict per wilaya. A wilaya
    already in the table is updated in place and a new one inserted, so the
    `updated_at` on an unchanged price still moves — the scrape happened, and
    that is worth being able to see.

    A wilaya the page no longer lists is left alone rather than deleted. The page
    omitting a wilaya is not the same as the site saying it stopped delivering
    there, and turning a scrape that silently matched fewer rows into a wipe of
    good data is the worse of the two mistakes.

    Raises:
        ReferenceDataMissing: If the wilayas have not been seeded. `wilaya_id` is a
          foreign key, so on a database where `create_all` has just made the tables
          and nobody has run the seed, every insert would fail with an
          `IntegrityError` naming a constraint. That says nothing an operator can
          act on, and it arrives after the site has already been scraped, so the
          check is up front and says which file to load.
    """
    cls._require_wilayas(db, rows)

    for row in rows:
      wilaya_id = row.get("wilaya_id")

      if wilaya_id is None:
        continue

      wilaya_id = int(wilaya_id)
      existing = cls.get(db, wilaya_id)

      if existing is None:
        existing = cls(wilaya_id=wilaya_id)
        db.add(existing)

      existing.available = bool(row.get("available", False))
      existing.price = row.get("price")
      existing.office_price = row.get("office_price")

    db.commit()

    return len(rows)

  @classmethod
  def _require_wilayas(cls, db, rows):
    """Refuse to sync into an unseeded database, and say how to fix it."""
    from src.models.wilaya import Wilaya

    wanted = sorted({int(row["wilaya_id"]) for row in rows
                     if row.get("wilaya_id") is not None})

    if not wanted:
      return

    known = set(
      db.execute(select(Wilaya.id).where(Wilaya.id.in_(wanted))).scalars()
    )

    if known:
      return

    raise ReferenceDataMissing(
      f"None of the {len(wanted)} wilayas on the shipping page are in the "
      f"database, so no price can be attached to one. Load the reference data "
      f"once, into an empty database:\n"
      f"  sqlite3 database/sawa9ly.db < src/seeds/wilayas_communes.sql\n"
      f"Then run this again. The seed is not applied automatically: it is 1541 "
      f"rows the site publishes rather than something this client scrapes."
    )

  def as_dict(self):
    return {
      "id": self.id,
      "wilaya_id": self.wilaya_id,
      "wilaya_name": self.wilaya.name if self.wilaya else None,
      "available": self.available,
      "price": float(self.price) if self.price is not None else None,
      "office_price": float(self.office_price) if self.office_price is not None else None,
    }

  def __repr__(self):
    return f"<DeliveryPrice wilaya={self.wilaya_id} available={self.available}>"