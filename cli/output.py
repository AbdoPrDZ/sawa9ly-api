"""Rendering command results for the terminal.

The commands return plain dicts and lists; this turns them into something
readable. A table where the data is tabular, and a key/value block otherwise,
so `user list` and `order show` both look deliberate.
"""

from tabulate import tabulate

# Cells wider than this are truncated; product descriptions are enormous.
MAX_CELL = 70


class Output:
  """Formats a command result for the terminal.

  Use `--json` on any command to get the raw structure back instead, which is
  what to pipe into jq or feed to something else.
  """

  @staticmethod
  def render(data, as_json=False):
    """Return the text to print."""
    if as_json:
      return Output.json(data)

    text = Output._render(data)

    return text if text is not None else Output.json(data)

  @staticmethod
  def json(data):
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)

  @staticmethod
  def _render(data):
    if data is None:
      return None

    if isinstance(data, list):
      return Output._table(data)

    if isinstance(data, dict):
      # A single wrapper key holding a list, e.g. {"users": [...]}.
      if len(data) == 1:
        only = next(iter(data.values()))
        if isinstance(only, list):
          return Output._table(only, key=next(iter(data)))

      maps = {k: v for k, v in data.items() if isinstance(v, dict)}

      # Sibling maps that share keys, e.g. the cart's quantities and prices:
      # show them as one table so the ids line up. Scalars ride underneath.
      if len(maps) > 1:
        lines = [Output._aligned(maps)]
        scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
        if scalars:
          lines.append(Output._pairs(scalars))
        return "\n".join(lines)

      return Output._pairs(data)

    return str(data)

  @staticmethod
  def _aligned(maps):
    """Render sibling dicts as a table: one column per map, one row per key.

    e.g. the cart's quantities and prices become columns headed by the map
    names, with a row per product id.
    """
    names = list(maps.keys())

    row_keys = []
    for value in maps.values():
      for key in value:
        if key not in row_keys:
          row_keys.append(key)

    headers = ["id"] + names
    body = [
      [key] + [Output._cell(maps[name].get(key)) for name in names]
      for key in row_keys
    ]

    return tabulate(body, headers=headers, tablefmt="simple")

  @staticmethod
  def _table(rows, key=None, indent=0):
    """One row per dict, or one column per dict for a list of scalars."""
    if not rows:
      return f"(no {key})" if key else "(nothing)"

    pad = "  " * indent

    if not isinstance(rows[0], dict):
      return tabulate(
        [[Output._cell(row)] for row in rows], headers=[key or "value"]
      )

    # Columns, in first-seen order so related rows line up.
    columns = []
    for row in rows:
      for column in row:
        if column not in columns:
          columns.append(column)

    nested = [c for c in columns if Output._is_records(rows, c)]

    body = [
      [len(row.get(c)) if c in nested else Output._cell(row.get(c)) for c in columns]
      for row in rows
    ]

    return pad + tabulate(body, headers=columns).replace("\n", "\n" + pad)

  @staticmethod
  def _is_records(rows, column):
    """True when a column holds nested records, so the table shows a count.

    Inlining them would repeat whole sub-tables inside one cell, which is how a
    listing of orders ends up unreadable. `order show` still prints them.
    """
    values = [row[column] for row in rows if row.get(column) is not None]
    if not values:
      return False

    return all(isinstance(v, list) and v and isinstance(v[0], dict) for v in values)

  @staticmethod
  def _pairs(data, indent=0):
    """Render a dict as `key: value` lines, with nested lists as tables."""
    lines = []
    pad = "  " * indent

    for key, value in data.items():
      if isinstance(value, list) and value and isinstance(value[0], dict):
        lines.append(f"{pad}{key}:")
        lines.append(Output._table(value, indent=indent + 1))
        continue

      if isinstance(value, dict):
        lines.append(f"{pad}{key}:")
        lines.append(Output._pairs(value, indent + 1))
        continue

      lines.append(f"{pad}{key}: {Output._cell(value)}")

    return "\n".join(lines)

  @staticmethod
  def _cell(value):
    """One value, flattened to a single line and length-capped."""
    if value is None:
      return "-"

    if isinstance(value, bool):
      return "yes" if value else "no"

    if isinstance(value, (list, tuple)):
      text = ", ".join(str(item) for item in value)
      return Output._shorten(text) if text else "-"

    if isinstance(value, dict):
      return Output._shorten(Output.json(value))

    return Output._shorten(" ".join(str(value).split()))

  @staticmethod
  def _shorten(text):
    """Cap a cell, so a row of image URLs does not become a wall of text."""
    if len(text) > MAX_CELL:
      return text[: MAX_CELL - 1] + "…"

    return text
