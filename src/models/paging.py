"""Paging a list query, and bounding what a caller may ask for.

Six list routes take `limit` and `offset` so a table can be shown a screen at a
time. Both are **optional and default to None, which means no limit at all** —
that is the load-bearing decision. These routes are the published `/api/v1`
contract, and a request without `?limit=` has to keep returning exactly what it
returned before this existed, or every existing consumer breaks at once.

So there is no total count in the response either: a bare JSON array cannot carry
one, and changing the shape to an envelope would be the breaking change this
avoids. The cost is that a caller learns "there are more rows" only by receiving a
full page, which is why `FULL_PAGE` below is a meaningful constant rather than an
arbitrary one — the UI treats a short page as "this is the last one".
"""

#: The largest page a caller may request.
#:
#: Without a cap, `?limit=1000000` is a request the database will try to honour,
#: and the list routes are reachable with nothing but a valid API key. A cap is
#: not a policy about how much data exists; it is a bound on what one request can
#: cost.
MAX_PAGE_SIZE = 200

#: The page size the dashboard asks for by default. Comfortably more than fits on
#: a large screen, so paging is rare, and comfortably less than `MAX_PAGE_SIZE`.
DEFAULT_PAGE_SIZE = 50

class Page:
  """One page of rows, and how many there were before paging.

  A bare list cannot say "there are more", and that is the whole reason this
  exists. It is returned as a dict by `as_dict`, which is the shape the HTTP list
  routes answer with — see `Page` in `src/schemas.py`, which is the wire version
  of this and the one a client is typed against.

  **This is a change to the published `/api/v1` list contract:** those routes used
  to answer with a bare JSON array and now answer with an object. A caller that
  expects an array has to read `items`. There is no way to carry a total in an
  array, so there was no non-breaking way to do this; `limit` and `offset` remain
  optional and a request without them still gets everything, which is the part
  that was worth keeping.
  """

  def __init__(self, items, total, limit=None, offset=0):
    self.items = list(items)
    self.total = total
    self.limit = Paging.cap(limit)
    self.offset = Paging.start(offset)

  @property
  def has_more(self):
    """Whether anything sits after this page.

    Computed from the total rather than from a short page, because a page can be
    short for a reason other than being the last one — a row deleted between two
    requests, or a search that matched fewer rows than were asked for.
    """
    return self.offset + len(self.items) < self.total

  def as_dict(self, shape):
    """The wire body: `items` through `shape`, with the paging alongside."""
    return {
      "items": [shape(row) for row in self.items],
      "total": self.total,
      "limit": self.limit,
      "offset": self.offset,
      "has_more": self.has_more,
    }

  def __len__(self):
    return len(self.items)

  def __iter__(self):
    return iter(self.items)

  def __repr__(self):
    return f"<Page {len(self.items)} of {self.total}>"


class Paging:
  """`LIMIT`/`OFFSET` for a select, with the bounds applied."""

  @staticmethod
  def cap(limit):
    """A usable limit, or None for "no limit".

    A non-positive or non-integer limit is treated as absent rather than rejected:
    it is a query parameter, and answering a bad one with everything is kinder
    than a 422 on a list a user is only browsing.
    """
    if limit is None:
      return None

    try:
      size = int(limit)
    except (TypeError, ValueError):
      return None

    if size <= 0:
      return None

    return min(size, MAX_PAGE_SIZE)

  @staticmethod
  def start(offset):
    """A usable offset, never negative."""
    if offset is None:
      return 0

    try:
      start = int(offset)
    except (TypeError, ValueError):
      return 0

    return max(0, start)

  @staticmethod
  def apply(query, limit=None, offset=None):
    """`query`, narrowed to one page.

    An offset with no limit is left to the database rather than being turned into
    a limit of one: `OFFSET n` alone is valid SQL and is occasionally what a
    caller means.
    """
    size = Paging.cap(limit)
    start = Paging.start(offset)

    if size is not None:
      query = query.limit(size)

    if start:
      query = query.offset(start)

    return query

  @staticmethod
  def run(db, query, limit=None, offset=None):
    """Count the rows `query` matches, then return one page of them.

    Two statements, and the count is the reason: `COUNT(*)` over a filtered
    query cannot be derived from the rows that came back, so a client that wants
    "page 3 of 9" has to be told the 9.

    The `order_by(None)` on the counted query is not cosmetic. The order is
    meaningless inside a `COUNT` and the database may be asked to sort the whole
    filtered set to do it.
    """
    from sqlalchemy import func, select

    total = db.execute(
      select(func.count()).select_from(query.order_by(None).subquery())
    ).scalar_one()

    rows = db.execute(Paging.apply(query, limit, offset)).scalars()

    return Page(rows, total, limit, offset)
