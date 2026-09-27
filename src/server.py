"""HTTP API for the sawa9ly client.

Run it with:

    python main.py serve

Every route except /health and /auth/login needs a credential. Machine callers
present an API key as `X-API-Key` (or `Authorization: Bearer ...`); the key
identifies the user, so each user's requests use that user's own sawa9ly session
and cart. The dashboard instead posts a username and password to /auth/login and
sends back a signed, expiring token on the /auth and /admin routes.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from src.config import Config
from src.controllers import (
  AdminKeysController,
  AdminUsersController,
  AuthController,
  CartController,
  CatalogueController,
  CheckoutController,
  ClientController,
  OrderController,
  ProductsController,
  TrackersController,
)
from src.controllers.dependencies import Dependencies
from src.logging_setup import configure_logging
from src.models import Role, User
from src.utils.livewire import Livewire, ensure_db
from src.version import VERSION

API_TITLE = "sawa9ly client API"
API_VERSION = VERSION

#: The HTTP contract version, in the path. Deliberately NOT derived from
#: `VERSION`: that is the application's version, and this is the version of the
#: wire format. They move independently — a bug fix ships as 1.3.1 with the
#: contract still at `/v1`.
#:
#: Applies to the machine-facing routes only. The dashboard's `/auth` and
#: `/admin` are unversioned, because the dashboard is their only caller.
API_PREFIX = "/v1"

# The dashboard's build output. Source lives in public/, but only dist/ is ever
# served, so node_modules and the sources are not exposed over HTTP.
PROJECT_ROOT = Config.PROJECT_ROOT
DASHBOARD_DIST = PROJECT_ROOT / "public" / "dist"
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
      "`python main.py apikey create`; the admin dashboard signs in at "
      "/auth/login and gets a token for /admin."
    ),
  )

  # The published contract. Every route here is reachable with a machine API
  # key, so they share one version prefix and a future `/v2` is added beside
  # this parent rather than in place of it.
  versioned = APIRouter(prefix=API_PREFIX)

  for controller in (
    ProductsController,
    CartController,
    CheckoutController,
    CatalogueController,
    ClientController,
    OrderController,
    TrackersController,
  ):
    versioned.include_router(controller.router)

  app.include_router(versioned)

  # The dashboard's own surface, deliberately NOT versioned. `/auth` and
  # `/admin` are reachable only with a dashboard token, and the sole caller is
  # the dashboard in public/ — there is no second consumer to keep compatible,
  # and versioning a private endpoint only buys a migration nobody needs. They
  # are mounted on the app directly, so their paths read as `/auth/login` and
  # `/admin/users` with no prefix to strip.
  for controller in (AuthController, AdminUsersController, AdminKeysController):
    app.include_router(controller.router)

  @app.get("/health", tags=["meta"])
  def health():
    """Liveness probe. No authentication required.

    Unversioned on purpose: this is what a load balancer, a container health
    check or an uptime monitor points at, and those are configured against a
    fixed path. Renaming it would break them without buying anything.
    """
    return {"status": "ok"}

  @app.get("/me", tags=["meta"])
  def me(user: User = Depends(Dependencies.get_current_user)):
    """The user the presented API key belongs to."""
    return {"username": user.username, "client": user.sawa9ly_email}

  _mount_dashboard(app)

  # A super account has to exist before anyone can administer anything, and the
  # dashboard is the only way in, so this runs as the app is built. It is a
  # no-op once a super exists, and it never resets an existing password.
  _bootstrap_super()

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
  """Serve the built dashboard, if it has been built.

  Registered last, and only when `public/dist` exists, so the API is fully
  usable with no frontend build at all. Any path that is not a real file falls
  back to index.html, which is what a client-side router needs in order to
  handle its own navigation.
  """
  if not DASHBOARD_DIST.is_dir():
    return

  assets = DASHBOARD_DIST / "assets"

  if assets.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets)), name="dashboard-assets")

  @app.get("/", include_in_schema=False)
  @app.get("/{path:path}", include_in_schema=False)
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


app = create_app()


if __name__ == "__main__":
  import uvicorn

  configure_logging()

  uvicorn.run(
    "src.server:app",
    host=Config.host(),
    port=Config.port(),
    reload=Config.reload(),
  )
