"""Schema steps for an existing database.

This is **not a migration framework** and must not become one. It is the
hand-run `ALTER TABLE` that `database.md` describes, written down so it can be
applied inside the container with no `psql` and with the application's own
connection, which already knows the credentials.

`create_all` creates missing **tables** and nothing else, so a database that
predates a project's columns keeps the old shape and the first query against a
model fails with "column does not exist". That is the case this exists for: the
two changes below were made to the models against a fresh SQLite file, and a
Postgres deployment that was built before them has to be brought forward.

Every step is idempotent and safe to re-run. Steps are ordered so a failure
leaves the database as it was (both engines give DDL transactions).

The steps
---------
1. `users` gains `store_name`, `store_slug`, `store_logo` and the unique index on
   `store_slug` — the public storefront identity (see `domains/storefront.md`).
2. `products` gains `cost`, and `price` moves from the site's display text to a
   whole-dinar number. Existing rows are parsed with `Product.parse_price`: the
   old text becomes `cost`, and `price` (the sell price) starts equal to it, the
   same default a first scrape would give.
"""

from sqlalchemy import inspect, text


class Migrations:
  """The ordered steps, and a runner that reports what it did."""

  @classmethod
  def run(cls):
    """Bring the database up to the models. Returns a report for the CLI."""
    from src.db import engine, init_db

    # Missing tables are `create_all`'s job, and doing it first is what makes the
    # column steps below a no-op on a database that is genuinely new. An existing
    # table is left exactly as it is.
    init_db()

    applied = []

    with engine.begin() as connection:
      applied += cls._users(connection)
      applied += cls._products(connection)

    return {
      "database": engine.dialect.name,
      "applied": applied or ["nothing to do; the schema is current"],
    }

  # --- steps ----------------------------------------------------------

  @classmethod
  def _users(cls, connection):
    """The three store columns and the slug's unique index."""
    applied = []

    columns = cls._columns(connection, "users")

    for name, ddl in (
      ("store_name", "VARCHAR(255)"),
      ("store_slug", "VARCHAR(64)"),
      ("store_logo", "TEXT"),
    ):
      if name not in columns:
        connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        applied.append(f"users.{name} added")

    # The model declares `unique=True, index=True`, which SQLAlchemy names
    # `ix_users_store_slug`. Both an index and a unique constraint are checked, so
    # a database created by an earlier naming does not get a second one.
    existing = cls._index_names(connection, "users")

    if "ix_users_store_slug" not in existing:
      connection.execute(
        text("CREATE UNIQUE INDEX ix_users_store_slug ON users (store_slug)")
      )
      applied.append("ix_users_store_slug created")

    return applied

  @classmethod
  def _products(cls, connection):
    """`cost`, and the move of `price` from text to whole dinars."""
    from src.models import Product

    applied = []

    columns = cls._columns(connection, "products")

    if not columns:
      return applied

    if "cost" not in columns:
      connection.execute(text("ALTER TABLE products ADD COLUMN cost INTEGER"))
      applied.append("products.cost added")
      columns = cls._columns(connection, "products")

    if "price" not in columns:
      return applied

    if "INT" in str(columns["price"]["type"]).upper():
      return applied

    # A stale temporary column from an interrupted run is dropped rather than
    # reused, so a second attempt starts from a known state.
    if "price_tmp" in columns:
      connection.execute(text("ALTER TABLE products DROP COLUMN price_tmp"))

    connection.execute(text("ALTER TABLE products ADD COLUMN price_tmp INTEGER"))

    # Read the raw text before the column is replaced, and parse it in Python —
    # the site's `'9,500 دج'` is not something the database can cast.
    rows = connection.execute(text("SELECT id, price FROM products")).fetchall()

    for row in rows:
      parsed = Product.parse_price(row.price)
      connection.execute(
        text(
          "UPDATE products SET cost = COALESCE(cost, :cost), price_tmp = :price "
          "WHERE id = :id"
        ),
        {"cost": parsed, "price": parsed, "id": row.id},
      )

    connection.execute(text("ALTER TABLE products DROP COLUMN price"))
    connection.execute(text("ALTER TABLE products RENAME COLUMN price_tmp TO price"))
    applied.append(f"products.price converted to INTEGER ({len(rows)} row(s) parsed)")

    return applied

  # --- reflection -----------------------------------------------------

  @staticmethod
  def _columns(connection, table):
    """The table's columns, as name -> reflected column.

    A fresh inspector each call, because these run while the migration's own DDL
    is uncommitted: a stale inspector would not see a column that was just added
    on this same connection.
    """
    return {column["name"]: column for column in inspect(connection).get_columns(table)}

  @staticmethod
  def _index_names(connection, table):
    """Every index and unique-constraint name on a table."""
    inspector = inspect(connection)

    names = {index["name"] for index in inspector.get_indexes(table)}
    names |= {
      constraint["name"] for constraint in inspector.get_unique_constraints(table)
    }

    return names
