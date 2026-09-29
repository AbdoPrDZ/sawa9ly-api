"""The public side: a published page, served at `/pages/{public_id}`.

This is what the reserved root namespace is for. It is registered last so that
`/api/...` and `/dashboard/...` are matched before it — a request for either of
those must never reach here.

Only a page in the `publish` state is served; see `LandingPageService.published`.

**The sandbox header is not decoration.** The dashboard and these pages share an
origin, and the dashboard keeps its token in `localStorage`. Without
`Content-Security-Policy: sandbox`, any script in a published page runs on that
same origin and can read that token — so a page an admin visits would hand over
their session. `sandbox` gives the page a unique, opaque origin with no script
execution, which renders HTML and CSS as written while making the dashboard's
origin unreachable from it.

The cost is that a page cannot run its own JavaScript. The way to have that is to
serve pages from a *different* origin, not to loosen this header: a second port
or host is a real origin boundary, and `sandbox` is not.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.services import LandingPageService

#: Applied to every published page. `sandbox` with no allowances is a unique
#: origin, no scripts, no forms, no plugins.
PAGE_CSP = "sandbox"

PAGE_HEADERS = {
  "Content-Security-Policy": PAGE_CSP,
  # The page is served as text/html deliberately; do not let a browser decide
  # otherwise from the content.
  "X-Content-Type-Options": "nosniff",
  # Unpublishing has to take effect, so the page is revalidated rather than
  # served from a heuristic cache after its state changes.
  "Cache-Control": "no-cache",
}

#: What someone gets at a public address that serves no page. Deliberately a
#: plain page rather than the API's JSON: this URL is followed by people, not by
#: clients, and `{"detail": "Not found."}` is not an answer to give a reader. The
#: status is still 404, and it says no more than the JSON did — an unpublished
#: page and one that never existed are indistinguishable here too.
#:
#: Static markup with nothing interpolated, so there is no escaping to get wrong.
#: It carries the same sandbox header as a real page, because it is served from
#: the dashboard's origin and must be just as unable to reach it.
NOT_FOUND_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Not found</title>
    <style>
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #0f1216;
        color: #e6e9ee;
        font: 16px/1.6 system-ui, sans-serif;
      }
      main { text-align: center; padding: 2rem; }
      h1 { font-size: 1.4rem; margin: 0 0 0.5rem; }
      p { color: #8b95a3; margin: 0; }
    </style>
  </head>
  <body>
    <main>
      <h1>Not found</h1>
      <p>There is no page at this address.</p>
    </main>
  </body>
</html>
"""


class PublicPageController:
  """A published landing page, addressed by its public id."""

  # Mounted on the app itself, not under `/api`, because a page is not an API
  # response. The prefix is `/pages` rather than the bare root so this namespace
  # stays claimable: a landing page at `/{public_id}` would swallow every path
  # the site might ever want at the root.
  #
  # Note this is `/pages/...` and not `/api/v1/pages/...` — the latter is the
  # signed-in user's own pages, a different resource behind a different
  # credential, and the two must not be confused.
  router = APIRouter(prefix="/pages", tags=["public"])

  @router.get("", response_class=HTMLResponse, include_in_schema=False)
  def index():
    """`/pages` on its own is not an address a page lives at.

    Declared so it answers like the rest of this namespace rather than falling
    through to the framework's JSON 404, which is not something to show a reader.
    """
    return HTMLResponse(content=NOT_FOUND_HTML, status_code=404, headers=PAGE_HEADERS)

  @router.get("/{public_id}", response_class=HTMLResponse, include_in_schema=False)
  def show(public_id: str, db: Session = Depends(Dependencies.get_db)):
    """One published page's markup, exactly as the author wrote it."""
    page = LandingPageService.published(db, public_id)

    if page is None:
      # Returned rather than raised, so the reader gets a page and not JSON.
      # Everything unpublished or unknown answers identically.
      return HTMLResponse(content=NOT_FOUND_HTML, status_code=404, headers=PAGE_HEADERS)

    return HTMLResponse(content=page.html, headers=PAGE_HEADERS)
