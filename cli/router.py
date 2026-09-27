"""CLI: the API's route table."""

# NOTE: `src.server` is deliberately NOT imported at module level. `cli/app.py`
# imports every group when it builds the parser, and importing `src.server`
# runs `create_app()` — which opens the database and bootstraps a super account.
# A module-level import here would make `user list` and `order show` need a
# database too, so the import happens inside `dispatch` instead.


class RouterCli:
  """`router` — list the HTTP routes the API serves.

  A developer command rather than a domain operation, so there is no service
  behind it and nothing mirrors it in the API: the route table is the assembled
  app, and an endpoint that reports it would only add a route to the list.

  Reading the OpenAPI schema rather than `app.routes` is what keeps this honest
  in two ways. It is the same contract `/docs` publishes, so the command cannot
  disagree with the documentation; and included routers are held as wrapper
  objects rather than flattened routes, so `app.routes` is not a stable thing to
  read the paths out of.

  What it cannot show is authentication. The routes authenticate through
  `Depends`, which leaves no security scheme in the schema, so there is no
  honest way to derive "needs an API key" from here — inferring it from the
  controller would be a second source that could disagree with the dependency.
  """

  @staticmethod
  def register(commands):
    commands.add_parser('router', help="list the API's routes")

  @staticmethod
  def dispatch(args):
    from src.server import app

    return RouterCli._rows(app.openapi().get("paths", {}))

  @staticmethod
  def _rows(paths):
    """One row per method, ordered by path then method.

    The OpenAPI paths object is keyed by path, then by method, so flattening it
    gives the grouping for free: the methods of one path stay on adjacent rows.
    `parameters` is a path-level key rather than an operation, so it is skipped.
    """
    rows = []

    for path in sorted(paths):
      for method, operation in sorted(paths[path].items()):
        if not isinstance(operation, dict) or method == 'parameters':
          continue

        rows.append({
          'method': method.upper(),
          'path': path,
          'tags': operation.get('tags') or [],
          'summary': operation.get('summary') or '',
        })

    return rows
