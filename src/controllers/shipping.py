"""Delivery price endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.models import Commune, DeliveryPrice, ReferenceDataMissing, Wilaya
from src.schemas import (
  CommuneOut,
  DeliveryPriceOut,
  DeliveryPriceSyncIn,
  Page,
  WilayaOut,
)
from src.services import Shipping
from src.utils import LivewireError
from src.utils.client_cache import ClientCache


class ShippingController:
  """What the site charges to deliver to each wilaya.

  The prices are the site's alone — one list for everybody — so the rows are
  shared and a sync run by one user is read by all of them. What the credential
  decides is narrower than that: it says who may read the list, and whose session
  fetches it.

  Auth is `get_any_user`, so an API key and a dashboard token both work, because
  the dashboard has a Shipping screen that calls both routes. It is safe for the
  same reason `/api/v1/clients` and `/api/v1/orders` are: the rows belong to no
  user, so there is no `user_id` for either credential to be scoped by, and
  nothing here can reach another user's data. What the credential still decides is
  who may read the list at all.

  **A sync uses the caller's own sawa9ly session, not a borrowed one.**
  `User.browsable` exists for the operations that read the site on behalf of
  nobody in particular, and this is not one of them: the credential names a user,
  so there is a session to use and nothing left to borrow. It is the same reasoning
  `save_catalogue_product` gives on the MCP side, and it arrives here by the same
  route — the catalogue's HTTP route carries no `Depends`, so it has to borrow.
  """

  router = APIRouter(prefix="/shipping", tags=["shipping"])

  @staticmethod
  def _sync(user):
    """Scrape the price list and store it."""
    # Checked before the client is built rather than caught off the login: a user
    # with no sawa9ly credentials is a setup problem with a known fix, not the
    # site having gone wrong, and the two are different answers (409 and 502).
    # `credentials()` raises with the command to run, so the message is not
    # restated here.
    try:
      user.credentials()
    except LivewireError as error:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=str(error),
      ) from error

    try:
      return Shipping(ClientCache.get(user.username)).get_prices()
    except LivewireError as error:
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error),
      ) from error

  @router.get("", response_model=Page[DeliveryPriceOut])
  def list_prices(available: bool | None = None, limit: int | None = None,
                  offset: int | None = None,
                  user=Depends(Dependencies.get_any_user),
                  db=Depends(Dependencies.get_db)):
    """The saved delivery prices. Free: nothing is fetched.

    `available` narrows the list to the wilayas the site delivers to, or to the
    ones it does not. `limit` and `offset` page the result. All three are
    optional, and passing none of them returns every row.

    Unavailable wilayas are not hidden by default: "we do not deliver there" is
    the answer somebody checking coverage is looking for.
    """
    return DeliveryPrice.page(db, available=available, limit=limit,
                              offset=offset).as_dict(lambda price: price.as_dict())

  @router.post("", response_model=Page[DeliveryPriceOut])
  def sync_prices(_body: DeliveryPriceSyncIn | None = None,
                  user=Depends(Dependencies.get_any_user),
                  db=Depends(Dependencies.get_db)):
    """Scrape the site's price list and store it. Costs one request to sawa9ly.

    Answers with the prices as they now stand. A wilaya that was not scraped is
    left alone rather than removed — a scrape that matched fewer rows is not the
    site saying it stopped delivering there.

    409 when the reference data has not been loaded: that is a setup step with a
    known command, not the site having broken, and the two are different answers.
    """
    try:
      DeliveryPrice.sync(db, ShippingController._sync(user))
    except ReferenceDataMissing as error:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=str(error),
      ) from error

    return ShippingController.list_prices(user=user, db=db)

  @router.get("/wilayas", response_model=list[WilayaOut])
  def list_wilayas(user=Depends(Dependencies.get_any_user),
                   db=Depends(Dependencies.get_db)):
    """The 58 wilayas. Free, and the whole list: it is small and never paged.

    A bare array rather than a `Page`, because there are 58 of them and they never
    change between syncs. Paging a fixed list of this size would be a control with
    nothing to control.
    """
    return [wilaya.as_dict() for wilaya in Wilaya.all(db)]

  @router.get("/communes", response_model=list[CommuneOut])
  def list_communes(wilaya_id: int | None = None,
                    user=Depends(Dependencies.get_any_user),
                    db=Depends(Dependencies.get_db)):
    """Communes, or one wilaya's communes when `wilaya_id` is given.

    **The filter exists because the site cannot answer the question itself.** It
    has no commune list page and no search, so which communes belong to a wilaya is
    not something a scrape can read — see `domains/catalogue.md`. Without the
    filter this returns all 1541, which is a usable answer to "every commune" and a
    useless one to "the communes of the wilaya somebody just picked".

    An unknown `wilaya_id` answers an empty list rather than a 404: the ids come
    from the list beside it, and a stale one means the caller is out of date, not
    that the wilaya was deleted.
    """
    return [commune.as_dict() for commune in Commune.all(db, wilaya_id)]