"""Product entity: catalogue information saved from a product page."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Product(Base):
  """A product's scraped details, kept so an order can be built offline.

  The catalogue is shared by all users, so there is no user_id here; only the
  sawa9ly `product_id` is unique. The landing pages written about a product are
  the exception: those belong to a user, so they hang off `landing_pages` and
  carry the user themselves.
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

  # No cascade: a product outlives the pages written about it, and removing one
  # should not silently take a user's writing with it.
  landing_pages: Mapped[list["LandingPage"]] = relationship(back_populates="product")
  # No cascade either: a notification is a record of something a user was told,
  # and the product can be deleted out from under it. The FK is SET NULL and the
  # message text is kept verbatim, so the record stays readable afterwards.
  notifications: Mapped[list["Notification"]] = relationship(back_populates="product")

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
  def all(cls, db, limit=None, offset=None, search=None):
    """Every saved product, optionally narrowed and paged.

    `search` matches the sawa9ly id exactly or the title loosely, so typing
    either `5663` or a word of the title finds the row. See `Search` and
    `Paging`, which own the escaping, the OR and the bounds.
    """
    from src.models.paging import Paging
    from src.utils.search import Search

    return list(db.execute(Paging.apply(cls._filtered(search), limit, offset)).scalars())

  @classmethod
  def page(cls, db, limit=None, offset=None, search=None):
    """One page of saved products, and the total before paging.

    Separate from `all` because `all` is what the CLI and the queue read, and it
    has to keep returning a plain list. Only the HTTP list route needs the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(search), limit, offset)

  @classmethod
  def _filtered(cls, search=None):
    """The select every list of products shares.

    One method because `all` and `page` must agree on what a search matches — two
    copies of a filter is how a list route ends up searching on a column the CLI
    does not, and the two quietly disagree.
    """
    from src.utils.search import Search

    query = select(cls).order_by(cls.product_id)

    match = Search.match(
      Search.equals_int(cls.product_id, search),
      Search.like(cls.title, search),
    )

    if match is not None:
      query = query.where(match)

    return query

  @staticmethod
  def parse_price(text):
    """The numeric price out of the site's display text, or None.

    The site writes prices the way it displays them — `'9,500 دج'`, `'585 دج'` —
    which is text, not a number, and carries a currency abbreviation. This pulls
    the digits out so a price can be compared or subtracted.

    Separators are disambiguated by position rather than assumed, because both
    conventions turn up on sites like this one. With both a comma and a dot
    present the last one is the decimal point, since that is the rightmost and
    therefore the innermost. With only one kind, a group of exactly three digits
    after it is a thousands separator and anything shorter is a decimal point.
    Either way only the whole part is kept: an order line sells in whole units,
    and dropping cents is better than rounding them into the total.

    Returns None when there is no number in the text at all — "sur demande",
    "prix non disponible" — because "we do not know" and "it is zero" are
    different facts and only one of them is true.
    """
    if not text:
      return None

    # Keep only what a number can be made of; the currency and spacing go.
    cleaned = "".join(char for char in str(text) if char.isdigit() or char in ",. ").replace(" ", "")

    if not any(char.isdigit() for char in cleaned):
      return None

    commas = [index for index, char in enumerate(cleaned) if char == ","]
    dots = [index for index, char in enumerate(cleaned) if char == "."]

    if commas and dots:
      # Both conventions in one string: the rightmost mark is the decimal point.
      whole = cleaned[: max(commas[-1], dots[-1])]
    else:
      marks = commas or dots

      if not marks:
        whole = cleaned
      elif len(marks) > 1 or len(cleaned) - marks[-1] - 1 == 3:
        # Repeated, or a group of three: thousands separators. Drop them all.
        whole = cleaned
      else:
        # A short trailing group: a decimal point. Keep what is before it.
        whole = cleaned[: marks[-1]]

    digits = "".join(char for char in whole if char.isdigit())

    return int(digits) if digits else None

  def numeric_price(self):
    """This product's price as a number, or None if the display text has none."""
    return Product.parse_price(self.price)

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
