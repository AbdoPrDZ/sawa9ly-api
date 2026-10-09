"""The public storefront: the store directory, a store's products, and its orders.

A store belongs to a user and lists the products that user has written a landing
page for. Browsing is open to anyone — the whole point — and so is placing an
order from a store's default product page.

**The public order is the one dangerous operation here, and everything around it
is shaped by that.** It runs as the store's owner, through that owner's single
sawa9ly session, and it posts a real order that cannot be cancelled from this
project. So:

- it is serialised per owner with a lock, because two visitors ordering at once
  would otherwise drive one cart and one session together;
- the form never reaches an owner who cannot take orders (no sawa9ly credentials,
  or a product with no price), which the controller checks before rendering it;
- the controller throttles and honeypots it, because this service cannot tell a
  customer from a bot.

A store is addressed by its technical name (`store_slug`); the display name is
what a visitor reads and is not unique, so it is never the key.
"""

import json
import threading

from sqlalchemy import select

from src.models import (
  Client,
  Commune,
  LandingPage,
  PageState,
  Product,
  User,
  Wilaya,
)
from src.models.paging import Paging
from src.services.order import OrderService
from src.utils.search import Search


class StorefrontError(Exception):
  """A storefront request cannot be carried out."""


class Storefront:
  """Reading stores, and placing an order from one."""

  #: One lock per owner, so a store's public orders are placed one at a time. The
  #: session and cart belong to the owner, not the visitor, so two orders at once
  #: are two writers to the same thing.
  _locks: dict = {}
  _locks_guard = threading.Lock()

  @classmethod
  def _lock_for(cls, username):
    with cls._locks_guard:
      lock = cls._locks.get(username)

      if lock is None:
        lock = threading.Lock()
        cls._locks[username] = lock

      return lock

  # --- the directory --------------------------------------------------

  @staticmethod
  def list_stores(db, search=None, limit=None, offset=None):
    """One page of stores, as the directory shows them."""
    page = User.stores(db, limit=limit, offset=offset, search=search)

    return {
      "items": [Storefront._store_card(user) for user in page.items],
      "total": page.total,
      "limit": page.limit,
      "offset": page.offset,
      "has_more": page.has_more,
    }

  @staticmethod
  def _store_card(user):
    return {
      "name": user.store_name,
      "slug": user.store_slug,
      "logo": user.store_logo,
    }

  # --- one store ------------------------------------------------------

  @staticmethod
  def store(db, slug):
    """The store at a URL segment, or None.

    A store is only real when both names are set, so a slug that matches a
    half-filled account is not a store.
    """
    user = User.by_store_slug(db, slug)

    if user is None or not user.has_store():
      return None

    return user

  @staticmethod
  def products(db, user, search=None, limit=None, offset=None):
    """One page of the products this store carries, with the page to show.

    A product is carried when the owner has written a landing page for it. One
    product can have several pages; the card's link uses the most recently
    updated **published** one, and falls back to the default page when there is
    none.
    """
    query = (
      select(Product)
      .join(LandingPage, LandingPage.product_id == Product.id)
      .where(LandingPage.user_id == user.id)
      .distinct()
      .order_by(Product.product_id)
    )

    match = Search.match(
      Search.equals_int(Product.product_id, search),
      Search.like(Product.title, search),
    )

    if match is not None:
      query = query.where(match)

    page = Paging.run(db, query, limit, offset)
    published = Storefront._published_pages(db, user.id, [p.id for p in page.items])

    return {
      "items": [
        Storefront._product_card(product, published.get(product.id))
        for product in page.items
      ],
      "total": page.total,
      "limit": page.limit,
      "offset": page.offset,
      "has_more": page.has_more,
    }

  @staticmethod
  def _published_pages(db, user_id, product_pks):
    """The public id to show per product, choosing the newest published page."""
    if not product_pks:
      return {}

    pages = db.execute(
      select(LandingPage)
      .where(
        LandingPage.user_id == user_id,
        LandingPage.product_id.in_(product_pks),
        LandingPage.state == PageState.PUBLISH,
      )
      .order_by(LandingPage.updated_at.desc())
    ).scalars()

    chosen = {}

    for page in pages:
      chosen.setdefault(page.product_id, page.public_id)

    return chosen

  @staticmethod
  def _product_card(product, public_id):
    images = json.loads(product.images or "[]")

    return {
      "product_id": product.product_id,
      "title": product.title,
      "price": product.price,
      "available": product.available,
      "image": images[0] if images else None,
      "public_id": public_id,
    }

  @staticmethod
  def product_for_store(db, user, product_id):
    """The product, only if this store carries it (a page exists for it).

    This is the check that stops a public order naming any product in the
    catalogue: a store may only sell what its owner has put in it.
    """
    product = Product.get(db, product_id)

    if product is None:
      return None

    carried = db.execute(
      select(LandingPage.id)
      .where(LandingPage.user_id == user.id, LandingPage.product_id == product.id)
      .limit(1)
    ).scalar_one_or_none()

    return product if carried is not None else None

  @staticmethod
  def public_page(db, user, product_pk):
    """The public id of the newest published page for a product, or None."""
    page = db.execute(
      select(LandingPage)
      .where(
        LandingPage.user_id == user.id,
        LandingPage.product_id == product_pk,
        LandingPage.state == PageState.PUBLISH,
      )
      .order_by(LandingPage.updated_at.desc())
      .limit(1)
    ).scalar_one_or_none()

    return page.public_id if page is not None else None

  @staticmethod
  def detail(product):
    """The product fields the default page renders, cost and margin excluded."""
    return {
      "product_id": product.product_id,
      "title": product.title,
      "price": product.price,
      "available": product.available,
      "description": product.description,
      "images": json.loads(product.images or "[]"),
    }

  # --- ordering -------------------------------------------------------

  @staticmethod
  def can_order(store, product):
    """Whether the checkout form should be offered, and why not when it is not.

    Two reasons a store cannot take an order, both reported rather than let the
    submit fail obscurely: the owner has no sawa9ly session to place it with, or
    the product has no sell price to charge.
    """
    if not (store.sawa9ly_email and store.sawa9ly_password):
      return False, "This store is not taking orders yet."

    if product is None or product.price is None:
      return False, "This product has no price set."

    return True, ""

  @staticmethod
  def validate_order(db, form):
    """A submitted form as (client fields, errors).

    `client fields` is None when anything is wrong, and `errors` is a field ->
    message map the form can show against its inputs. Wilaya and commune are
    checked against the reference data rather than trusted, and the pair is
    checked against each other — the site rejects a commune that is not in the
    chosen wilaya, so that is caught here instead.
    """
    errors = {}

    full_name = (form.get("full_name") or "").strip()
    phone = (form.get("phone") or "").strip()
    adresse = (form.get("adresse") or "").strip()

    if not full_name:
      errors["full_name"] = "Your name is required."
    if not phone:
      errors["phone"] = "A phone number is required."
    if not adresse:
      errors["adresse"] = "An address is required."

    wilaya_id = Storefront._int_or_none(form.get("wilaya_id"))
    commune_id = Storefront._int_or_none(form.get("commune_id"))

    wilaya = Wilaya.get(db, wilaya_id) if wilaya_id is not None else None
    commune = Commune.get(db, commune_id) if commune_id is not None else None

    if wilaya is None:
      errors["wilaya_id"] = "Choose a wilaya."

    if commune is None:
      errors["commune_id"] = "Choose a commune."
    elif wilaya is not None and commune.wilaya_id != wilaya.id:
      errors["commune_id"] = "That commune is not in the chosen wilaya."

    if errors:
      return None, errors

    return {
      "full_name": full_name,
      "phone": phone,
      "adresse": adresse,
      "wilaya_id": wilaya.id,
      "commune_id": commune.id,
    }, {}

  @staticmethod
  def _int_or_none(value):
    try:
      return int(str(value).strip())
    except (TypeError, ValueError):
      return None

  @classmethod
  def place_order(cls, db, store, product, fields):
    """Save the recipient, build a draft, and submit it as the store owner.

    The order is stored first, so it appears in the owner's dashboard with the
    address to fulfil it from, and only then posted. It is placed under the
    owner's lock, because the visitor is not the one whose cart and session are
    being driven.
    """
    with cls._lock_for(store.username):
      client = Client(user_id=store.id, **fields)
      db.add(client)
      db.commit()

      order = OrderService.create(db, store.username, client_id=client.id)
      OrderService.add_line(
        db, order.id, product.product_id, quantity=1, price=product.price,
      )

      return OrderService.checkout(db, order.id, store.username)
