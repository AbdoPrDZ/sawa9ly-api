"""HTTP API for the sawa9ly client.

Run it with:

    python main.py serve

Every route except /api/health and /api/auth/login needs a credential. Machine
callers present an API key as `X-API-Key` (or `Authorization: Bearer ...`); the key
identifies the user, so each user's requests use that user's own sawa9ly session
and cart. The dashboard instead posts a username and password to /api/auth/login
and sends back a signed, expiring token on the /api/auth and /api/admin routes.

Everything the application serves lives under /api or /dashboard; the site root
is for the public pages, and answers a published landing page by its public id.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from src.config import Config
from src.controllers import (
  AdminKeysController,
  AdminOrdersController,
  AdminUsersController,
  AuthController,
  CartController,
  CatalogueController,
  CheckoutController,
  ClientController,
  OrderController,
  PageController,
  ProductsController,
  PublicPageController,
  TelegramController,
  TrackersController,
)
from src.controllers.dashboard_log import DashboardLogger
from src.controllers.dependencies import Dependencies
from src.models import Role, User
from src.utils.livewire import Livewire, ensure_db
from src.version import VERSION

API_TITLE = "sawa9ly client API"
API_VERSION = VERSION

#: Every route this application serves that is not the dashboard or a future
#: public page sits under here. It exists so the API owns a known namespace and
#: the site root can be given to public pages without either moving later.
API_BASE = "/api"

#: The HTTP contract version, in the path. Deliberately NOT derived from
#: `VERSION`: that is the application's version, and this is the version of the
#: wire format. They move independently — a bug fix ships as 1.3.1 with the
#: contract still at `/v1`.
#:
#: Applies to the machine-facing routes only. The dashboard's `/auth` and
#: `/admin` are unversioned, because the dashboard is their only caller. Both sit
#: under `API_BASE`, so a controller's own prefix stays relative.
API_PREFIX = "/v1"

#: Where the dashboard is served. Its in-app routes are relative to this, so the
#: built assets and the router have to agree on it (see `base` in
#: `dashboard/vite.config.ts` and `basename` in `dashboard/src/main.tsx`).
DASHBOARD_BASE = "/dashboard"

# The dashboard's build output. Source lives in dashboard/, but only dist/ is ever
# served, so node_modules and the sources are not exposed over HTTP.
PROJECT_ROOT = Config.PROJECT_ROOT
DASHBOARD_DIST = PROJECT_ROOT / "dashboard" / "dist"
DASHBOARD_INDEX = DASHBOARD_DIST / "index.html"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Per-user Livewire clients, so each API key keeps its own session and cart.
_clients: dict[str, Livewire] = {}


def client_cache(username):
  """The Livewire client for a user, created (and logged in) on first use."""
  if username not in _clients:
    _clients[username] = Livewire(username)

  return _clients[username]


def create_app():
  ensure_db()

  app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
      "Scrape products, manage a cart and place orders on sawa9ly.app. "
      "Machine callers authenticate with an API key created by "
      f"`python main.py apikey create`; the admin dashboard signs in at "
      f"{API_BASE}/auth/login and gets a token for {API_BASE}/admin."
    ),
  )

  # The published contract. Every route here is reachable with a machine API
  # key, so they share one version prefix and a future `/v2` is added beside
  # this parent rather than in place of it. The outer `/api` is the namespace the
  # whole surface lives in, so it is prepended here rather than in each
  # controller: the controllers stay unaware of where they are mounted.
  versioned = APIRouter(prefix=API_BASE + API_PREFIX)

  for controller in (
    ProductsController,
    CartController,
    CheckoutController,
    CatalogueController,
    ClientController,
    OrderController,
    PageController,
    TelegramController,
    TrackersController,
  ):
    versioned.include_router(controller.router)

  app.include_router(versioned)

  # The dashboard's own surface, deliberately NOT versioned. `/auth` and
  # `/admin` are reachable only with a dashboard token, and the sole caller is
  # the dashboard in dashboard/ — there is no second consumer to keep compatible,
  # and versioning a private endpoint only buys a migration nobody needs. They
  # share the outer `/api` with everything else, and their own `/auth` and
  # `/admin` segments, so their paths read as `/api/auth/login` and
  # `/api/admin/users`.
  #
  # `require_admin` is the usual floor here; `/api/admin/orders` asks for
  # `require_super`, because it is the one route that crosses user boundaries.
  dashboard_api = APIRouter(prefix=API_BASE)

  for controller in (
    AuthController, AdminUsersController, AdminKeysController, AdminOrdersController
  ):
    dashboard_api.include_router(controller.router)

  app.include_router(dashboard_api)

  @app.get(f"{API_BASE}/health", tags=["meta"])
  def health():
    """Liveness probe. No authentication required.

    Sits under `/api` with everything else, but stays unversioned: this is what
    a load balancer, a container health check or an uptime monitor points at, and
    those are configured against a fixed path, so it must not move when the
    contract version does. Change `API_BASE` and the probe moves with it.
    """
    return {"status": "ok"}

  @app.get(f"{API_BASE}/me", tags=["meta"])
  def me(user: User = Depends(Dependencies.get_current_user)):
    """The user the presented API key belongs to."""
    return {"username": user.username, "client": user.sawa9ly_email}

  _mount_dashboard(app)
  _mount_root(app)

  # Registered absolutely last, because it is a catch-all at the site root. The
  # API and the dashboard must be matched before it, and they are, since their
  # routes are already in place. It answers only for a published page's
  # public_id under /pages/ and 404s everything else.
  app.include_router(PublicPageController.router)

  # A super account has to exist before anyone can administer anything, and the
  # dashboard is the only way in, so this runs as the app is built. It is a
  # no-op once a super exists, and it never resets an existing password.
  _bootstrap_super()

  # Added last, after every route is in place, so it wraps the finished app
  # rather than a half-built one.
  app.add_middleware(DashboardLogger)

  return app


def _bootstrap_super():
  """Create the environment-configured super account, if there is no super.

  A failure here stops the app on purpose. There has to be one account that can
  sign in and administer the rest, and if neither the database nor the
  environment provides one, starting anyway would only produce a dashboard that
  nobody can get into.
  """
  from src.services import Accounts

  created = Accounts.bootstrap_super()

  if created:
    sys.stderr.write(
      f"bootstrapped '{Role.SUPER}' account '{created}' from "
      f"{Config.SUPER_ADMIN_USERNAME_VAR}\n"
    )


def _mount_dashboard(app):
  """Serve the built dashboard at DASHBOARD_BASE, if it has been built.

  Registered last, and only when `dashboard/dist` exists, so the API is fully
  usable with no frontend build at all. Any path under the base that is not a
  real file falls back to index.html, which is what a client-side router needs in
  order to handle its own navigation.

  Scoped to the base on purpose. A catch-all across the whole site would answer
  every unknown path — a mistyped API route, and eventually the public pages —
  with the dashboard shell, so nothing else could ever be mounted at the root.
  """
  if not DASHBOARD_DIST.is_dir():
    return

  assets = DASHBOARD_DIST / "assets"

  # Mounted before the routes below, so a real asset is never mistaken for an
  # in-app route and handed the shell.
  if assets.is_dir():
    app.mount(
      f"{DASHBOARD_BASE}/assets",
      StaticFiles(directory=str(assets)),
      name="dashboard-assets",
    )

  @app.get(DASHBOARD_BASE, include_in_schema=False)
  def dashboard_entry():
    """Send the bare base to its trailing-slash form.

    The built assets are absolute, so this is about the router: `basename` is
    `/dashboard`, and a redirect keeps one spelling of the URL in the address bar.
    """
    return RedirectResponse(f"{DASHBOARD_BASE}/", status_code=307)

  @app.get(f"{DASHBOARD_BASE}/{{path:path}}", include_in_schema=False)
  def dashboard(path: str = ""):
    """The dashboard shell, or a built file if the path names one."""
    if path:
      candidate = (DASHBOARD_DIST / path).resolve()

      # The resolve() plus the containment check is what stops `../` from
      # walking out of the build directory and serving the rest of the project.
      if candidate.is_file() and DASHBOARD_DIST.resolve() in candidate.parents:
        return FileResponse(candidate)

    if not DASHBOARD_INDEX.is_file():
      raise HTTPException(status_code=404, detail="Not found.")

    return FileResponse(DASHBOARD_INDEX)


def _mount_root(app):
  """The site root, which is reserved for the public pages.

  It names where the dashboard is rather than serving it, because a dashboard at
  the root is exactly what the `/api` and `/dashboard` split exists to stop. It is
  registered whether or not the dashboard has been built, so the message is the
  same either way.

  Rendered as a page rather than raised, because the root is a URL a person types,
  not one a client calls — same reasoning as the public page's 404. It is the one
  place outside the public namespace that shows a human a message, and it is kept
  in step with `NOT_FOUND_HTML`'s styling on purpose.
  """

  @app.get("/", include_in_schema=False, response_class=HTMLResponse)
  def site_root():
    return HTMLResponse(
      content=f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>sawa9ly</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #0f1216;
        color: #e6e9ee;
        font: 16px/1.6 system-ui, sans-serif;
      }}
      main {{ text-align: center; padding: 2rem; }}
      h1 {{ font-size: 1.4rem; margin: 0 0 0.5rem; }}
      p {{ color: #8b95a3; margin: 0; }}
    </style>
  </head>
  <body>
    <main>
      <h1>sawa9ly</h1>
      <p>The dashboard is at <a style="color: #4f8cff" href="{DASHBOARD_BASE}/">{DASHBOARD_BASE}/</a>.</p>
    </main>
  </body>
</html>
""",
      status_code=404,
      headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
    )


app = create_app()


if __name__ == "__main__":
  import uvicorn

  from src.logging_setup import UVICORN_LOG_CONFIG, Logging

  Logging.configure()

  uvicorn.run(
    "src.server:app",
    host=Config.host(),
    port=Config.port(),
    reload=Config.reload(),
    log_config=UVICORN_LOG_CONFIG,
  )
