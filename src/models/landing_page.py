"""LandingPage entity: a user's own page for one product."""

import secrets
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow

#: Bytes of entropy behind a page's public_id. 16 bytes is 22 URL-safe
#: characters, which is far more than a landing page needs and short enough to
#: paste into a message.
PUBLIC_ID_BYTES = 16
PUBLIC_ID_LENGTH = 22

#: What a public_id may contain. The route checks a path against this before
#: touching the database, so `/favicon.ico` and every other stray request costs
#: nothing and cannot turn into a query.
PUBLIC_ID_CHARS = frozenset(
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


class PageState:
  """Where a page is in its life.

  draft    - being written, not served
  publish  - live
  archive  - taken down but kept

  There are no transition rules: a page may be moved to any of these at any
  time. That is a deliberate difference from `OrderState`, where the site's own
  flow decides what may follow what. Nothing external acts on a page yet, so
  there is no lifecycle to enforce beyond the state being one of these three.
  """

  DRAFT = "draft"
  PUBLISH = "publish"
  ARCHIVE = "archive"

  ALL = (DRAFT, PUBLISH, ARCHIVE)

  @staticmethod
  def is_valid(state):
    return state in PageState.ALL


class LandingPage(Base):
  """A landing page one user has written for one product.

  A page belongs to a user, not to the catalogue, so two users can write
  different pages for the same product and neither can see the other's. There is
  no uniqueness on (user_id, product_id) on purpose: one user may keep several
  pages for the same product — a seasonal offer, a second language, a variant.

  `product_id` is a foreign key to our own `products.id`, not to the sawa9ly
  id. The two are different keys and mixing them is the single most common
  mistake in this project, so the column is named for what it holds and the
  sawa9ly id is read through `product.product_id`.

  `public_id` is the opaque token the page is served under, and is unrelated to
  `id`: `id` is ours and enumerable, so it must never appear in a public URL.
  """

  __tablename__ = "landing_pages"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
  # The token this page is published under. Unique across every user's pages,
  # because it is looked up without a user in scope.
  public_id: Mapped[str] = mapped_column(String(PUBLIC_ID_LENGTH), unique=True, index=True)
  title: Mapped[str] = mapped_column(String(255))
  # The page's markup, stored as written. Served verbatim by the public route.
  html: Mapped[str] = mapped_column(Text, default="")
  state: Mapped[str] = mapped_column(String(16), default=PageState.DRAFT, index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

  user: Mapped["User"] = relationship(back_populates="landing_pages")
  product: Mapped["Product"] = relationship(back_populates="landing_pages")

  @staticmethod
  def generate_public_id():
    """A fresh unguessable public id."""
    return secrets.token_urlsafe(PUBLIC_ID_BYTES)

  @staticmethod
  def looks_like_public_id(value):
    """Whether a path segment could be a public id at all.

    Used to answer a stray request without a database round trip. It is a shape
    check, not a validity check: a well-formed token that matches no page is
    simply not found.
    """
    return len(value) == PUBLIC_ID_LENGTH and not (set(value) - PUBLIC_ID_CHARS)

  @classmethod
  def get(cls, db, page_id):
    return db.get(cls, int(page_id))

  @classmethod
  def get_by_public_id(cls, db, public_id):
    """Find a page by the token it is published under, or None."""
    return db.execute(
      select(cls).where(cls.public_id == public_id)
    ).scalar_one_or_none()

  @classmethod
  def all(cls, db, user_id=None, product_id=None, state=None,
          limit=None, offset=None, search=None):
    """Pages, newest first, optionally narrowed and paged.

    `search` matches the title and the product id exactly.
    """
    from src.models.paging import Paging

    return list(db.execute(
      Paging.apply(cls._filtered(user_id, product_id, state, search), limit, offset)
    ).scalars())

  @classmethod
  def page(cls, db, user_id=None, product_id=None, state=None,
           limit=None, offset=None, search=None):
    """One page of landing pages, and the total before paging.

    Separate from `all` because `all` is what the CLI reads and it keeps
    returning a plain list. Only the HTTP list route needs the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(user_id, product_id, state, search), limit, offset)

  @classmethod
  def _filtered(cls, user_id=None, product_id=None, state=None, search=None):
    """The select every list of landing pages shares."""
    from src.utils.search import Search

    query = select(cls).order_by(cls.id.desc())
    if user_id is not None:
      query = query.where(cls.user_id == user_id)
    if product_id is not None:
      query = query.where(cls.product_id == product_id)
    if state is not None:
      query = query.where(cls.state == state)

    match = Search.match(
      Search.like(cls.title, search),
      Search.equals_int(cls.product_id, search),
    )

    if match is not None:
      query = query.where(match)

    return query

  @classmethod
  def create(cls, db, user_id, product_pk, title, html="", public_id=None):
    """Start a draft page for a product.

    A public id is minted here rather than by the caller, and retried on the
    astronomically unlikely collision rather than trusted to be unique.
    """
    for _ in range(5):
      candidate = public_id or cls.generate_public_id()
      existing = db.execute(
        select(cls.id).where(cls.public_id == candidate)
      ).scalar_one_or_none()

      if existing is None:
        break
    else:
      raise ValueError("Could not mint a unique public id")

    page = cls(
      user_id=user_id, product_id=product_pk, title=title,
      html=html or "", public_id=candidate,
    )
    db.add(page)
    db.commit()
    return page

  def as_dict(self):
    return {
      "id": self.id,
      "user_id": self.user_id,
      "product_id": self.product_id,
      "public_id": self.public_id,
      "title": self.title,
      "html": self.html,
      "state": self.state,
      "created_at": str(self.created_at) if self.created_at else None,
      "updated_at": str(self.updated_at) if self.updated_at else None,
    }

  def __repr__(self):
    return f"<LandingPage {self.id} {self.state} {self.title!r}>"
