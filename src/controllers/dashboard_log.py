"""The dashboard's own request log.

The dashboard is a static single-page app served out of `dashboard/dist`. There is
no application code behind it to log, so the only server-side record of it is that
a browser asked for it — and without this, `sawa9ly-dashboard.log` would never
contain a line while `sawa9ly-api.log` carried every request for it.

This is deliberately a *separate* logger from the API's rather than a filter over
uvicorn's access log. Splitting that log would mean depending on the shape of
uvicorn's access-log arguments, which is an internal detail; writing our own line
means the format is ours, it is the same whatever runs the server, and it cannot
break when uvicorn changes.

What is logged is the browser-facing surface: the dashboard and its assets, and a
published landing page. A `/api` call from the dashboard is the API's business
and is already recorded there.

Written as raw ASGI rather than as `BaseHTTPMiddleware`, because a middleware that
only observes a request has no business buffering the response to do it —
`BaseHTTPMiddleware` would hold a streamed file in memory on the way past, and
this app serves the dashboard bundle.
"""

import logging
import time

logger = logging.getLogger(__name__)

#: The paths that are the dashboard or a published page, rather than the API.
DASHBOARD_PREFIX = "/dashboard"
PAGE_PREFIX = "/pages"


def is_browser_facing(path):
  """Whether a path is something a person loads, rather than an API call."""
  return path == DASHBOARD_PREFIX or path.startswith(DASHBOARD_PREFIX + "/") \
    or path == PAGE_PREFIX or path.startswith(PAGE_PREFIX + "/")


def _line(method, path, status, took_ms):
  """One log line, at a level chosen by what happened.

  Not everything is INFO: a 404 on a page path is a broken deep link and would
  otherwise sit unnoticed under a wall of cache revalidations, while a 304 is
  noise and should not be escalated. `None` means the app never sent a status at
  all, which is itself worth an error.
  """
  if status is None:
    logger.error("%s %s never sent a status (%.0fms)", method, path, took_ms)
  elif status == 404:
    logger.warning("%s %s -> 404 (%.0fms)", method, path, took_ms)
  elif status >= 500:
    logger.error("%s %s -> %s (%.0fms)", method, path, status, took_ms)
  else:
    logger.info("%s %s -> %s (%.0fms)", method, path, status, took_ms)


class DashboardLogger:
  """Middleware recording requests for the dashboard and published pages."""

  def __init__(self, app):
    self.app = app

  async def __call__(self, scope, receive, send):
    # Not an HTTP request (lifespan or websocket), or not a page: hand it on
    # untouched. The API's own records cover the rest.
    if scope["type"] != "http" or not is_browser_facing(scope.get("path", "")):
      return await self.app(scope, receive, send)

    method = scope.get("method", "-")
    path = scope.get("path", "-")
    started = time.perf_counter()
    status = None

    async def watch(message):
      nonlocal status

      # `http.response.start` carries the status; `http.response.body` follows
      # and does not. Recorded on the way through rather than buffered, so a
      # streamed file is unaffected.
      if message["type"] == "http.response.start":
        status = message.get("status")

      await send(message)

    try:
      await self.app(scope, receive, watch)
    except Exception as error:
      # Logged before re-raising, because an exception in a static-file mount is
      # exactly what this log exists to catch and a missing line reads as "nobody
      # asked for that page".
      logger.error(
        "%s %s failed after %.0fms: %s",
        method, path, (time.perf_counter() - started) * 1000, error,
      )
      raise

    _line(method, path, status, (time.perf_counter() - started) * 1000)
