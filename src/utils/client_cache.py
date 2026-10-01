"""One `Livewire` per user, for the life of a process.

Building a client may log in to sawa9ly.app, and a login is a request to the
site. Both long-running front ends — the HTTP API and the MCP server — serve
many calls per minute, so the client is kept rather than rebuilt per call.

It lives here rather than in `src/server.py` because two processes now need it,
and a module-level `client_cache()` in the server would mean the MCP server
importing the whole FastAPI app to reach one dictionary — which, since
`create_app()` runs at import of `src.server`, would also mean bootstrapping a
super account and mounting the dashboard to get a per-user session.
"""


class ClientCache:
  """The `Livewire` for each username, created on first use.

  A class rather than a dict so the cache has one name in the project: both front
  ends reach for the same object, and two dictionaries would mean two sessions
  and two carts for a user who happened to hit both surfaces.

  The store is per-process and deliberately not guarded. `requests.Session` is
  not thread-safe and FastAPI runs synchronous handlers on a threadpool, so two
  concurrent requests for one user can drive that session at once — see
  `architecture.md`. The cache narrows that to a user's own session rather than
  pretending to solve it, which is the trade this project already makes.
  """

  _clients: dict = {}

  @classmethod
  def get(cls, username):
    """The client for a user, built (and so logged in) on first use."""
    if username not in cls._clients:
      from src.utils.livewire import Livewire

      cls._clients[username] = Livewire(username)

    return cls._clients[username]

  @classmethod
  def forget(cls, username):
    """Drop one user's client, so the next call builds and logs in again.

    For a credential that has just been changed on the site, or a session the
    site has stopped honouring. Everything else should let the cache do its job —
    clearing it wholesale on any error would turn a transient site failure into a
    login on every subsequent call.
    """
    return cls._clients.pop(username, None)
