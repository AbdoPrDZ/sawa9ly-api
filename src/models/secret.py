"""App-wide secret storage."""

import secrets
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base, utcnow

# 32 bytes of entropy, hex encoded. A token signing key has to be unguessable
# but does not need to be human-readable, and it is never displayed.
SECRET_BYTES = 32


class Secret(Base):
  """One named secret belonging to the application, not to a user.

  This exists so generated secrets survive a restart. The alternative — a new
  random secret per process — would silently invalidate every session token
  whenever the server restarted.
  """

  __tablename__ = "app_secrets"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  value: Mapped[str] = mapped_column(String(255))
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  @classmethod
  def get(cls, db, name):
    """The named secret's row, or None. Looks up by name, not by primary key."""
    from sqlalchemy import select

    return db.execute(
      select(cls).where(cls.name == name)
    ).scalar_one_or_none()

  @classmethod
  def get_or_create(cls, db, name, factory=None):
    """The named secret's value, generating and storing it the first time.

    `factory` builds the value; the default is random hex. On a concurrent
    first run the loser's insert is rolled back and the winner's value is
    returned, so two processes never end up signing with different keys.
    """
    secret = cls.get(db, name)

    if secret is not None:
      return secret.value

    value = factory() if factory else secrets.token_hex(SECRET_BYTES)
    db.add(cls(name=name, value=value))

    try:
      db.commit()
    except Exception:
      db.rollback()
      existing = cls.get(db, name)
      return existing.value if existing else value

    return value

  def __repr__(self):
    # Never render the value: a repr in a log or a traceback would leak it.
    return f"<Secret {self.name}>"
