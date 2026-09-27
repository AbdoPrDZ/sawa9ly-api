"""Product endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import ProductInCartOut, ProductOut
from src.utils.livewire import LivewireError


class ProductsController:
  """Reading a product page and moving it in and out of the cart."""

  router = APIRouter(prefix="/products", tags=["products"])

  @staticmethod
  def _fail(error, code=status.HTTP_409_CONFLICT):
    return HTTPException(status_code=code, detail=str(error))

  @router.get("/{product_id}", response_model=ProductOut)
  def read(product=Depends(Dependencies.get_product)):
    """Scrape a product page."""
    try:
      info = product.get_info()
    except LivewireError as error:
      raise ProductsController._fail(error, status.HTTP_502_BAD_GATEWAY)

    return {"product_id": product.product_id, **info}

  @router.post("/{product_id}/cart", response_model=ProductInCartOut)
  def add_to_cart(product=Depends(Dependencies.get_product)):
    """Add a product to the caller's cart."""
    try:
      return product.add_to_cart()
    except LivewireError as error:
      raise ProductsController._fail(error)

  @router.delete("/{product_id}/cart", response_model=ProductInCartOut)
  def remove_from_cart(product=Depends(Dependencies.get_product)):
    """Remove a product from the caller's cart."""
    try:
      return product.remove_from_cart()
    except LivewireError as error:
      raise ProductsController._fail(error)
