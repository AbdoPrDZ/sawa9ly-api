"""Cart endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import CartOut, PriceIn, QuantityIn
from src.utils.livewire import LivewireError


class CartController:
  """Reading the caller's cart and editing its lines."""

  router = APIRouter(prefix="/cart", tags=["cart"])

  @staticmethod
  def _run(action, *args, **kwargs):
    """Run a cart action, turning a Livewire failure into an HTTP error."""
    try:
      return action(*args, **kwargs)
    except LivewireError as error:
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

  @router.get("", response_model=CartOut)
  def read(cart=Depends(Dependencies.get_cart)):
    """The caller's cart: quantities, prices, count and total."""
    return cart.get_info()

  @router.put("/items/{product_id}/quantity", response_model=dict)
  def set_quantity(product_id: int, body: QuantityIn, cart=Depends(Dependencies.get_cart)):
    """Set a cart line's quantity. Persisted server-side."""
    return CartController._run(cart.update_item_quantity, product_id, body.quantity)

  @router.put("/items/{product_id}/price", response_model=dict)
  def set_price(product_id: int, body: PriceIn, cart=Depends(Dependencies.get_cart)):
    """Set a cart line's unit price. Snapshot only; use checkout to commit."""
    return CartController._run(cart.update_item_price, product_id, body.price)

  @router.delete("/items/{product_id}", response_model=dict)
  def remove_item(product_id: int, cart=Depends(Dependencies.get_cart)):
    """Remove a cart line."""
    return CartController._run(cart.remove_item, product_id)
