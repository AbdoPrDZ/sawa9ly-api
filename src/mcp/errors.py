"""The refusals this layer raises on its own behalf.

The domain already has its own errors — `OrderError`, `PageError`,
`TrackingError`, `LivewireError` — and those are what a tool lets through, because
they already say what went wrong and what to do about it in the words the CLI and
the API use.

These two are for the refusals that are only expressible in HTTP terms. The
catalogue's 404 and its "nobody can browse" 409 exist because a route has to
answer with a status code; a tool call has no status, so without these the MCP
layer would either raise `HTTPException` — which a model reads as "404 Not Found:
Product 5663 is not saved", an HTTP artefact leaking into a protocol that has no
such thing — or return `{"error": ...}`, which is a *successful* call carrying a
failure the caller has to notice.
"""


class McpError(Exception):
  """A tool call that cannot be answered: a row that is not there, or a
  prerequisite this installation does not have.

  The message is the whole of it — there is no code and no status — so it has to
  say what to do next, because that text is all an agent sees.
  """


class McpAuthError(McpError):
  """A tool call that arrived without a usable MCP API key."""
