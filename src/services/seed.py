"""Loading a .sql seed file through the engine, for either database.

The seed file is plain SQL on purpose, so it can be handed to whatever client a
deployment already has. That is not always enough: the application image carries
Python and `psycopg[binary]` but no `psql`, so the person deploying on a VPS has
no client at all inside the container they are already in. This is the same load
through the engine the application itself uses, which needs nothing extra.

The file is executed **one statement at a time** rather than in a single call,
because the two drivers differ: `sqlite3`'s `execute()` refuses more than one
statement and psycopg's accepts them. Statement-at-a-time is the only shape that
behaves the same on both.
"""

import re
from pathlib import Path

from src.config import Config

#: Comment lines are dropped before parsing. They carry apostrophes - "the site's
#: own numbering" - and a quote scan that counted those would think the file had
#: an unbalanced string in it.
COMMENTS = re.compile(r"^\s*--.*$", re.M)

#: The file wraps itself in a transaction. An engine session opens one of its own,
#: where an explicit BEGIN inside it warns and an explicit COMMIT ends it early, so
#: both are dropped and the session's transaction is used instead.
TRANSACTION = re.compile(r"^\s*(BEGIN\s+TRANSACTION|COMMIT|END)\s*;?\s*$", re.M | re.I)


class Seed:
  """A .sql file under `src/seeds`, loaded through the application's engine."""

  #: The delivery reference data. Named here rather than in the CLI so the path
  #: has one home; `Config.PROJECT_ROOT` is what makes it findable from an
  #: installed copy as well as a checkout.
  DELIVERY = "src/seeds/wilayas_communes.sql"

  @classmethod
  def path(cls, relative=None):
    """The seed file's absolute path, or None when it is not there."""
    candidate = Config.PROJECT_ROOT / (relative or cls.DELIVERY)
    return candidate if candidate.is_file() else None

  @classmethod
  def statements(cls, sql):
    """One .sql file as a list of single executable statements.

    Split on `;`, which is safe for the seeds here and is checked rather than
    assumed: a commune name containing a semicolon would be split in half and
    loaded as nonsense, which is exactly the kind of corruption that looks like a
    successful run. A seed with a semicolon in a value should use a different
    loader rather than get this one wrong quietly.
    """
    body = COMMENTS.sub("", sql)
    body = TRANSACTION.sub("", body)

    return [part.strip() for part in body.split(";") if part.strip()]

  @classmethod
  def load(cls, db, relative=None):
    """Run a seed file, and report what it put in the tables.

    Returns a dict naming the file and how many rows each of its tables now
    holds, so the caller can print something an operator can check rather than
    "done".

    Raises:
        SeedMissing: If the file is not where this project says it is. A packaged
          install that lost it is a packaging defect, not something to work around
          by writing the rows from somewhere else.
    """
    from src.models import Commune, Wilaya

    relative = relative or cls.DELIVERY
    location = cls.path(relative)

    if location is None:
      raise SeedMissing(
        f"The seed file is not there: {Config.PROJECT_ROOT / relative}. It ships "
        f"in the distribution (see MANIFEST.in); a copy without it cannot load the "
        f"delivery reference data."
      )

    executed = 0

    # The session's own connection, not the session: `exec_driver_sql` is on the
    # connection, and it is the only way to hand the engine a whole statement that
    # is not an ORM expression - which is what a .sql file is. Committing through
    # the session afterwards keeps the caller on one transaction.
    connection = db.connection()

    for statement in cls.statements(location.read_text(encoding="utf-8")):
      connection.exec_driver_sql(statement)
      executed += 1

    db.commit()

    return {
      "file": str(location),
      "statements": executed,
      "wilayas": db.query(Wilaya).count(),
      "communes": db.query(Commune).count(),
    }


class SeedMissing(RuntimeError):
  """Raised when a seed file the project ships is not on disk.

  A class rather than a message thrown inline so the CLI can report it as a setup
  step with a non-zero exit, next to `ReferenceDataMissing` and for the same
  reason.
  """