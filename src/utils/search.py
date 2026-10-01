"""Filtering a list by what somebody typed into a search box.

A small helper rather than a `LIKE` written at each call site, because two things
are easy to get wrong and neither is visible until a user searches for the wrong
thing:

- **The wildcards.** `%` and `_` are `LIKE` metacharacters, so a search for
  `50%` or `a_b` would match far more than the user asked for. `like` here
  escapes them and names the escape character, so a query matches the text that
  was typed and nothing else.
- **Case.** A user typing `sawa` wants `Sawa9ly`, and the opposite is rarer and
  harmless. `ilike` lower-cases both sides rather than relying on the database's
  collation, which differs between SQLite and PostgreSQL — and this project runs
  on both.

`term` returns None for a blank or whitespace-only query, and every `all()`
classmethod treats None as "no filter". That is what makes the search box
optional on the wire: a request with no `q` behaves exactly as it did before,
which matters because these list routes are also the machine-facing contract.
"""

#: Backslash. Not special in SQL itself, so it is free to use as the escape
#: character — and it has to be escaped itself, or a query ending in `\` would
#: escape the closing `%` and match nothing.
ESCAPE = "\\"


class Search:
  """A user's search box, turned into a query."""

  @staticmethod
  def term(raw):
    """The cleaned-up term, or None when there is nothing to search for.

    Trimmed, and capped. The cap is not arbitrary politeness: an unbounded term
    is interpolated into a `LIKE` pattern, and a very long one is a query nobody
    meant to send. Sixty-four characters is past anything a person would type to
    find a row.
    """
    if raw is None:
      return None

    cleaned = raw.strip()

    if not cleaned or len(cleaned) > 64:
      return None

    return cleaned

  @staticmethod
  def like(column, term):
    """`column LIKE %term%`, case-insensitively, with the wildcards escaped.

    Returns None for a blank term so a caller can `if clause is not None` rather
    than always applying a `LIKE '%%'` that would scan every row and match
    everything.

    Pass the result to `or_()` when a row is searchable on more than one column —
    an id *or* a title, say — so typing either finds the row.
    """
    cleaned = Search.term(term)

    if cleaned is None or column is None:
      return None

    escaped = (
      cleaned.replace(ESCAPE, ESCAPE + ESCAPE).replace("%", f"{ESCAPE}%").replace("_", f"{ESCAPE}_")
    )

    return column.ilike(f"%{escaped}%", escape=ESCAPE)

  @staticmethod
  def equals_int(column, term):
    """`column = int(term)`, or None when the term is not a whole number.

    The other half of searching a table whose key is numeric: `Product 5663` has
    to be findable by typing `5663`, and a `LIKE '%5663%'` would also match
    `15663` or a title containing those digits. An exact numeric match is what
    somebody typing an id means.
    """
    cleaned = Search.term(term)

    if cleaned is None or column is None:
      return None

    try:
      return column == int(cleaned)
    except ValueError:
      return None

  @staticmethod
  def match(*clauses):
    """Every usable clause, OR'd into the one thing to filter on — or None.

    This exists because of a bug it is shaped to make impossible. Applying each
    clause in turn, `for clause in clauses: query = query.where(or_(clause))`,
    ANDs them: each `or_` wraps a single clause, which is a no-op, and successive
    `.where()` calls are conjunctive. So searching a products table for `25` would
    demand `product_id = 25` *and* a title containing `25`, and quietly return
    nothing for a row that plainly matches.

    Pass the candidates for one row — every column that should match, plus
    `equals_int` on the key — and this joins them the way a person means:

    ```python
    match = Search.match(
      Search.equals_int(Product.product_id, term),
      Search.like(Product.title, term),
    )
    if match is not None:
      query = query.where(match)
    ```

    None means "no usable clause", which is the caller's signal to skip the
    `.where()` entirely rather than filter on something always-true.
    """
    from sqlalchemy import or_

    live = [clause for clause in clauses if clause is not None]

    if not live:
      return None

    if len(live) == 1:
      return live[0]

    return or_(*live)
