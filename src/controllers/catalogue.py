"""Saved catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import Page, ProductOut, ProductSaveIn, ProductUpdateIn
from src.services import Product
from src.utils import Livewire, LivewireError, PageNotFound


class CatalogueController:
  """Scraping a product once, then serving it from the database."""

  router = APIRouter(prefix="/catalogue", tags=["catalogue"])

  @staticmethod
  def _scrape(db, product_id):
    """Read a product page from the site.

    Nobody is named in the request, so the browsing session comes from whichever
    user has complete sawa9ly credentials. That is only transport — it decides
    whose session to read the page with, never whose data to touch.
    """
    from src.models import User as UserRow

    username = UserRow.browsable(db)

    if username is None:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
          "No user has sawa9ly credentials, so no product can be fetched. "
          "Record them with: python main.py user add <username> --email ... "
          "--password ..."
        ),
      )

    try:
      return Product(product_id, Livewire(username)).get_info()
    except PageNotFound as error:
      # Before this was its own case, the site answering 404 escaped as a bare
      # 500 with a traceback in the message. It is not a broken site and it is
      # not a bad request in the API sense either: the id asked for is simply not
      # a product, which is a 404, and the only useful thing to say about it is
      # which id failed and where to check it.
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {product_id} does not exist on sawa9ly.app. "
               "Check the id in the product's URL on the site.",
      ) from error
    except LivewireError as error:
      # Everything else about reaching the site: an expired session it would not
      # refresh, a timeout, a connection it refused, HTML it would not parse.
      # The site is unusable rather than the product absent, which is what a 502
      # is for.
      raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))


  @staticmethod
  def _lookup(db, product_id):
    from src.models import Product as ProductRow

    product = ProductRow.get(db, product_id)

    if product is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        # No path is spelled out here on purpose. The router's own prefix is
        # /catalogue and it is mounted under a version and a namespace, so any
        # absolute path written into this message is one that can quietly go
        # stale; naming the action cannot.
        detail=f"Product {product_id} is not saved. POST it first, to scrape "
               "and store its page.",
      )

    return product

  @router.get("", response_model=Page[ProductOut])
  def list_products(q: str | None = None, limit: int | None = None,
                    offset: int | None = None,
                    db=Depends(Dependencies.get_db)):
    """Every saved product.

    `q` searches the sawa9ly id and the title; `limit` and `offset` page the
    result. All three are optional, and passing none of them returns every row —
    the rows are under `items` either way, because a count cannot be carried in a
    bare array.
    """
    from src.models import Product as ProductRow

    return ProductRow.page(db, limit=limit, offset=offset, search=q).as_dict(
      lambda product: product.as_dict()
    )

  @router.get("/{product_id}", response_model=dict)
  def read(product_id: int, db=Depends(Dependencies.get_db)):
    """A saved product."""
    return CatalogueController._lookup(db, product_id).as_dict()

  @router.post("/{product_id}", response_model=dict)
  def save(product_id: int, _body: ProductSaveIn | None = None,
           db=Depends(Dependencies.get_db)):
    """Scrape a product page and store the result."""
    from src.models import Product as ProductRow

    info = CatalogueController._scrape(db, product_id)
    return ProductRow.save(db, product_id, info).as_dict()

  @router.patch("/{product_id}", response_model=dict)
  def set_price(product_id: int, body: ProductUpdateIn,
                db=Depends(Dependencies.get_db)):
    """Set a saved product's sell price.

    The cost is the site's and is not editable here; only `price` is accepted,
    which is why this is a PATCH and not a general product update.
    """
    product = CatalogueController._lookup(db, product_id)
    product.set_price(db, body.price)

    return product.as_dict()
