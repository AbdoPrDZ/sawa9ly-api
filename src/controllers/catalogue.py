"""Saved catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import ProductSaveIn
from src.services import Product
from src.utils import Livewire
from src.utils.livewire import LivewireError


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
    except LivewireError as error:
      raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))


  @staticmethod
  def _lookup(db, product_id):
    from src.models import Product as ProductRow

    product = ProductRow.get(db, product_id)

    if product is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {product_id} is not saved; POST /catalogue/{product_id} first.",
      )

    return product

  @router.get("", response_model=list)
  def list_products(db=Depends(Dependencies.get_db)):
    """Every saved product."""
    from src.models import Product as ProductRow

    return [p.as_dict() for p in ProductRow.all(db)]

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
