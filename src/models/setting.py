"""Setting entity: per-user key/value storage."""

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base

# The login session cookie lives here rather than in a file on disk.
SESSION_KEY = "sawa9ly_session"

# Which language this user reads and is written to in. A setting rather than a
# column on `users`, so that adding a language is not a schema change — the same
# reason the session cookie is here. See `src/i18n.py`.
LOCALE_KEY = "sawa9ly_locale"


class Setting(Base):
  """A single named value belonging to a user.

  Used to persist the sawa9ly session cookie (SESSION_KEY) and any other
  per-user configuration.
  """

  __tablename__ = "settings"
  __table_args__ = (UniqueConstraint("user_id", "key", name="uq_settings_user_key"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  key: Mapped[str] = mapped_column(String(64))
  value: Mapped[str | None] = mapped_column(Text, default=None)

  user: Mapped["User"] = relationship(back_populates="settings")

  @classmethod
  def get(cls, db, user_id, key, default=None):
    """Read one setting for a user, or `default` when it is not set."""
    row = db.execute(
      select(cls).where(cls.user_id == user_id, cls.key == key)
    ).scalar_one_or_none()

    return row.value if row is not None else default

  @classmethod
  def set(cls, db, user_id, key, value):
    """Create or update one setting for a user."""
    row = db.execute(
      select(cls).where(cls.user_id == user_id, cls.key == key)
    ).scalar_one_or_none()

    if row is None:
      row = cls(user_id=user_id, key=key, value=value)
      db.add(row)
    else:
      row.value = value

    db.commit()

    return row

  def __repr__(self):
    return f"<Setting {self.key} user={self.user_id}>"
