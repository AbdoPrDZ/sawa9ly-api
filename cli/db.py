"""CLI: database maintenance."""


class DbCli:
  """`db` — bring an existing database up to the models.

  A developer/operator command, like `router`: it has no API or MCP equivalent
  because it is not a domain operation, and nothing mirrors it. It exists so a
  deployment whose database predates a column change can be brought forward with
  the application's own connection — the image ships `psycopg` and no `psql`, so
  the alternative would be a client that is not installed.

  `db migrate` is idempotent and safe to re-run. See `src/services/migrations.py`
  for exactly what it changes; it is deliberately a short, explicit list rather
  than a migration framework.
  """

  @staticmethod
  def register(commands):
    db = commands.add_parser('db', help="database maintenance")
    actions = db.add_subparsers(dest='action', required=True)

    actions.add_parser(
      'migrate', help="apply pending schema changes to an existing database"
    )

  @staticmethod
  def dispatch(args):
    from src.services.migrations import Migrations

    if args.action == 'migrate':
      return Migrations.run()
