"""The public storefront routes.

These are the only pages this project serves that are for people rather than
callers, and they are open: no credential, the whole point. The directory at `/`,
a store at `/stores/{slug}`, a store's default product page at
`/stores/{slug}/{product_id}`, and the checkout form's POST.

**Everything here is carefully small.** The browsing routes read local tables and
never touch sawa9ly. The one route that reaches the site is the order POST, which
runs as the store owner and posts a real order — so it is throttled, honeypotted,
and refused outright when the owner cannot actually take orders. See
`src/services/storefront.py` for why it is serialised per owner.

`Content-Security-Policy: sandbox allow-forms` is on every page. `sandbox` alone
is what the authored `/pages/...` pages get, and it is enough there because they
only ever render. The checkout form has to submit, which the bare sandbox forbids,
so `allow-forms` is added — and nothing else. There is still no script and no
same-origin access, so a storefront page cannot reach the dashboard's token.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import Commune, Wilaya
from src.services.order import OrderError
from src.services.storefront import Storefront
from src.services.storefront_pages import PAGE_SIZE, StorefrontPages
from src.utils.livewire import LivewireError
from src.utils.throttle import Throttle

PAGE_HEADERS = {
  "Content-Security-Policy": "sandbox allow-forms",
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "no-cache",
}


class StorefrontController:
  """The public storefront: stores, their products, and their orders."""

  router = APIRouter(tags=["storefront"])

  #: Orders per IP and per store, as a spam brake. Both are checked; whichever
  #: trips answers the same way. See `src/utils/throttle.py` for the limits'
  #: meaning — in-memory, per-process, forgotten on restart.
  _by_ip = Throttle(limit=5, window=60)
  _by_store = Throttle(limit=60, window=3600)

  # --- the store directory --------------------------------------------

  @router.get("/", response_class=HTMLResponse, include_in_schema=False)
  def home(q: str | None = None, offset: int = 0,
           db: Session = Depends(Dependencies.get_db)):
    """Every store, as cards."""
    stores = Storefront.list_stores(db, search=q, limit=PAGE_SIZE, offset=offset)

    return StorefrontController._page(StorefrontPages.directory(stores, (q or "").strip()))

  # --- one store ------------------------------------------------------

  @router.get("/stores/{slug}", response_class=HTMLResponse, include_in_schema=False)
  def store(slug: str, q: str | None = None, offset: int = 0,
            db: Session = Depends(Dependencies.get_db)):
    """A store's products, with a search box."""
    user = Storefront.store(db, slug)

    if user is None:
      return StorefrontController._not_found()

    products = Storefront.products(db, user, search=q, limit=PAGE_SIZE, offset=offset)

    return StorefrontController._page(StorefrontPages.store(user, products, (q or "").strip()))

  @router.get("/stores/{slug}/{product_id}", response_class=HTMLResponse,
              include_in_schema=False)
  def product(slug: str, product_id: int,
              db: Session = Depends(Dependencies.get_db)):
    """A product's page: the owner's published one, or a generated default.

    A published page is a real page the owner wrote, and it is served from its
    own address, so this redirects to it rather than copying its markup here.
    """
    user = Storefront.store(db, slug)

    if user is None:
      return StorefrontController._not_found()

    product_row = Storefront.product_for_store(db, user, product_id)

    if product_row is None:
      return StorefrontController._not_found()

    public_id = Storefront.public_page(db, user, product_row.id)

    if public_id:
      return RedirectResponse(f"/pages/{public_id}", status_code=302)

    return StorefrontController._render_product(db, user, product_row)

  # --- ordering -------------------------------------------------------

  @router.post("/stores/{slug}/{product_id}/order", response_class=HTMLResponse,
               include_in_schema=False)
  def order(slug: str, product_id: int, request: Request,
            full_name: str = Form(""), phone: str = Form(""),
            adresse: str = Form(""), wilaya_id: str = Form(""),
            commune_id: str = Form(""), website: str = Form(""),
            db: Session = Depends(Dependencies.get_db)):
    """Place an order from a store's default product page.

    No credential: the store is the context. The order runs as the store's owner,
    which is why the form is only accepted when that owner can actually take
    orders, and why it is throttled.
    """
    user = Storefront.store(db, slug)

    if user is None:
      return StorefrontController._not_found()

    product_row = Storefront.product_for_store(db, user, product_id)

    if product_row is None:
      return StorefrontController._not_found()

    can_order, reason = Storefront.can_order(user, product_row)

    if not can_order:
      return StorefrontController._error(reason, status_code=409)

    # Honeypot first, so a bot that fills the hidden field is neither throttled
    # nor told it was caught. It is shown the same page a real order gets.
    if (website or "").strip():
      return StorefrontController._page(
        StorefrontPages.success(user, Storefront.detail(product_row))
      )

    ip = request.client.host if request.client else "unknown"

    if not StorefrontController._by_ip.allow(ip):
      return StorefrontController._error(
        "Too many orders have been placed from here just now. Please try again "
        "in a minute.", status_code=429,
      )

    if not StorefrontController._by_store.allow(slug):
      return StorefrontController._error(
        "This store is receiving a lot of orders right now. Please try again "
        "later.", status_code=429,
      )

    values = {
      "full_name": full_name,
      "phone": phone,
      "adresse": adresse,
      "wilaya_id": wilaya_id,
      "commune_id": commune_id,
    }
    fields, errors = Storefront.validate_order(db, values)

    if errors:
      return StorefrontController._render_product(
        db, user, product_row, values=values, errors=errors, status_code=400,
      )

    try:
      result = Storefront.place_order(db, user, product_row, fields)
    except LivewireError as error:
      # The site refused or could not be reached. The order is stored as a draft
      # and can be retried from the dashboard; the visitor is told it did not go
      # through rather than shown a blank success.
      return StorefrontController._render_product(
        db, user, product_row, values=values, message=str(error), status_code=502,
      )
    except OrderError as error:
      return StorefrontController._render_product(
        db, user, product_row, values=values, message=str(error), status_code=409,
      )

    checkout = result.get("checkout") or {}

    if checkout.get("success"):
      return StorefrontController._page(
        StorefrontPages.success(user, Storefront.detail(product_row))
      )

    return StorefrontController._render_product(
      db, user, product_row, values=values,
      message=StorefrontController._site_errors(checkout.get("errors")),
      status_code=409,
    )

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _render_product(db, user, product_row, values=None, errors=None,
                      message=None, status_code=200):
    can_order, reason = Storefront.can_order(user, product_row)
    wilayas = Wilaya.all(db) if can_order else []
    communes = Commune.all(db) if can_order else []

    html = StorefrontPages.product(
      user, Storefront.detail(product_row), wilayas, communes,
      can_order, reason, values, errors, message,
    )

    return StorefrontController._page(html, status_code=status_code)

  @staticmethod
  def _site_errors(errors):
    """The site's validation errors as one sentence, or a generic refusal."""
    if not errors:
      return "The order could not be placed. Please check your details."

    parts = []

    for field, messages in errors.items():
      if isinstance(messages, (list, tuple)):
        parts.extend(f"{field}: {message}" for message in messages)
      else:
        parts.append(f"{field}: {messages}")

    return " ".join(parts)

  @staticmethod
  def _page(html, status_code=200):
    return HTMLResponse(content=html, status_code=status_code, headers=PAGE_HEADERS)

  @staticmethod
  def _not_found():
    return StorefrontController._page(StorefrontPages.not_found(), status_code=404)

  @staticmethod
  def _error(message, status_code):
    return StorefrontController._page(
      StorefrontPages.error(message), status_code=status_code,
    )
