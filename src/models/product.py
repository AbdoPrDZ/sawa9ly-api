"""Product entity: catalogue information saved from a product page."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base, utcnow


class Product(Base):
  """A product's scraped details, kept so an order can be built offline.

  The catalogue is shared by all users, so there is no user_id here; only the
  sawa9ly `product_id` is unique.
  """

  __tablename__ = "products"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  product_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
  title: Mapped[str | None] = mapped_column(String(512), default=None)
  price: Mapped[str | None] = mapped_column(String(64), default=None)
  description: Mapped[str | None] = mapped_column(Text, default=None)
  # Stored as JSON text so this stays portable across SQLite and Postgres.
  images: Mapped[str | None] = mapped_column(Text, default=None)
  figures: Mapped[str | None] = mapped_column(Text, default=None)
  categories: Mapped[str | None] = mapped_column(Text, default=None)
  available: Mapped[bool] = mapped_column(Boolean, default=True)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

  @classmethod
  def get(cls, db, product_id):
    """Find a saved product by its sawa9ly id, or None."""
    return db.execute(
      select(cls).where(cls.product_id == int(product_id))
    ).scalar_one_or_none()

  @classmethod
  def get_by_id(cls, db, pk):
    """Find a saved product by our own primary key, or None.

    The tracking queue resolves a tracker's `target_id`, which is this key
    rather than the sawa9ly one.
    """
    return db.get(cls, pk)

  @classmethod
  def get_or_create(cls, db, product_id):
    """Return the saved product for a sawa9ly id, creating a stub if needed."""
    product = cls.get(db, product_id)

    if product is None:
      product = cls(product_id=int(product_id))
      db.add(product)
      db.commit()

    return product

  @classmethod
  def save(cls, db, product_id, info):
    """Create or update a product from a get_info() result."""
    import json

    product = cls.get_or_create(db, product_id)

    product.title = info.get("title")
    product.price = info.get("price")
    product.description = info.get("description")
    product.available = bool(info.get("availability", True))
    product.images = json.dumps(info.get("images") or [], ensure_ascii=False)
    product.figures = json.dumps(info.get("figures") or [], ensure_ascii=False)
    product.categories = json.dumps(info.get("categories") or [], ensure_ascii=False)
    db.commit()

    return product

  @classmethod
  def all(cls, db, limit=None):
    query = select(cls).order_by(cls.product_id)
    if limit:
      query = query.limit(limit)
    return list(db.execute(query).scalars())

  def as_dict(self):
    """Catalogue fields as plain values."""
    import json

    return {
      'product_id': self.product_id,
      'title': self.title,
      'price': self.price,
      'description': self.description,
      'images': json.loads(self.images or "[]"),
      'figures': json.loads(self.figures or "[]"),
      'categories': json.loads(self.categories or "[]"),
      'available': self.available,
    }

  def __repr__(self):
    return f"<Product {self.product_id} {self.title!r}>"
