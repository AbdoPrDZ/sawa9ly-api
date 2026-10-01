"""ApiKey entity for authenticating API requests."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow

PREFIX_LENGTH = 8
KEY_PREFIX = "sk_"


class ApiKey(Base):
  """A hashed API key belonging to a user.

  Only the SHA-256 hash is stored, so a database leak cannot be replayed as a
  key; the plaintext is shown once at creation.
  """

  __tablename__ = "api_keys"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  prefix: Mapped[str] = mapped_column(String(PREFIX_LENGTH), index=True)
  label: Mapped[str | None] = mapped_column(String(64), default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
  expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
  revoked: Mapped[bool] = mapped_column(Boolean, default=False)

  user: Mapped["User"] = relationship(back_populates="api_keys")

  # --- creation and lookup ------------------------------------------

  @staticmethod
  def generate():
    """Return a (plaintext, hashed) pair for a brand new key."""
    plaintext = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return plaintext, ApiKey.hash(plaintext)

  @staticmethod
  def hash(plaintext):
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

  @staticmethod
  def prefix_of(plaintext):
    return plaintext[:PREFIX_LENGTH]

  @classmethod
  def create(cls, db, user_id, label=None, expires_in_days=None):
    """Create a key for a user and return (entity, plaintext)."""
    plaintext, hashed = cls.generate()

    key = cls(
      user_id=user_id,
      key_hash=hashed,
      prefix=cls.prefix_of(plaintext),
      label=label,
      expires_at=(utcnow() + timedelta(days=expires_in_days)) if expires_in_days else None,
    )
    db.add(key)
    db.commit()

    return key, plaintext

  @classmethod
  def find(cls, db, plaintext):
    """Look up a key by its plaintext, or None."""
    return db.execute(
      select(cls).where(cls.key_hash == cls.hash(plaintext))
    ).scalar_one_or_none()

  @classmethod
  def all(cls, db, user_id=None, limit=None, offset=None, search=None):
    """Every key, optionally narrowed to one user, optionally narrowed and paged.

    `search` matches the prefix or the label. **Not the key itself** — only its
    hash is stored, so there is nothing to match against, and a search that
    appeared to work on the plaintext would be a promise the database cannot keep.
    """
    from src.models.paging import Paging

    return list(db.execute(
      Paging.apply(cls._filtered(user_id, search), limit, offset)
    ).scalars())

  @classmethod
  def page(cls, db, user_id=None, limit=None, offset=None, search=None):
    """One page of API keys, and the total before paging.

    Separate from `all` because `all` is what the CLI reads and it keeps
    returning a plain list. Only the HTTP list routes need the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(user_id, search), limit, offset)

  @classmethod
  def _filtered(cls, user_id=None, search=None):
    """The select every list of API keys shares."""
    from src.utils.search import Search

    query = select(cls).order_by(cls.id)
    if user_id is not None:
      query = query.where(cls.user_id == user_id)

    match = Search.match(
      Search.like(cls.prefix, search),
      Search.like(cls.label, search),
    )

    if match is not None:
      query = query.where(match)

    return query

  # --- state ---------------------------------------------------------

  def is_valid(self):
    """Whether the key may still be used."""
    if self.revoked:
      return False

    if self.expires_at is not None:
      expires = self.expires_at
      if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
      if expires <= utcnow():
        return False

    return True

  def touch(self):
    """Record that the key was just used."""
    self.last_used_at = utcnow()

  def __repr__(self):
    return f"<ApiKey {self.prefix}… user={self.user_id}>"
