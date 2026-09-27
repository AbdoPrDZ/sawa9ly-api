"""Checkout endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import CheckoutIn, CheckoutOut
from src.utils.livewire import LivewireError


class CheckoutController:
  """Setting the cart's quantities/prices and submitting the order form."""

  router = APIRouter(tags=["checkout"])

  @router.post("/checkout", response_model=CheckoutOut)
  def checkout(body: CheckoutIn, cart=Depends(Dependencies.get_cart)):
    """Set quantities and prices, fill the order form and submit.

    A complete, valid `client` places a real order that cannot be cancelled
    from here. Use `dry_run` to stage the cart without submitting.
    """
    try:
      result = cart.checkout(
        quantities=body.quantities,
        prices=body.prices,
        client=body.client.model_dump(exclude_none=True),
        dry_run=body.dry_run,
      )
    except LivewireError as error:
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    return result
