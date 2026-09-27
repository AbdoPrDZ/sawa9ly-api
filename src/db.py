"""Database engine and session factory."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import Config

DEFAULT_DATABASE_URL = Config.sqlite_url()


def utcnow():
  """Timezone-aware current time, used as a column default."""
  return datetime.now(timezone.utc)


def database_url():
  """The database URL, resolved from the environment.

  See `Config.database_url`: `DATABASE_URL` wins, then the discrete `DB_*`
  variables, then a SQLite file under `data/`.
  """
  return Config.database_url()


def _engine_kwargs(url):
  # SQLite needs check_same_thread disabled for FastAPI's threadpool, and
  # foreign keys enabled, otherwise ON DELETE CASCADE never fires and deleting
  # a user would orphan its settings and keys.
  if not url.startswith("sqlite"):
    return {}

  return {"connect_args": {"check_same_thread": False}}


def _enable_sqlite_foreign_keys():
  """Turn on PRAGMA foreign_keys for every new SQLite connection."""
  from sqlalchemy import event

  if not database_url().startswith("sqlite"):
    return

  @event.listens_for(engine, "connect")
  def _set_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_engine(database_url(), future=True, **_engine_kwargs(database_url()))

_enable_sqlite_foreign_keys()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
  """Declarative base for every ORM entity."""


def init_db():
  """Create any missing tables. Safe to call repeatedly."""
  # Imported for the side effect of registering the entities on Base.metadata.
  from src import models  # noqa: F401

  Base.metadata.create_all(engine)


def session_scope():
  """A transactional session, as a context manager."""
  return SessionLocal()
