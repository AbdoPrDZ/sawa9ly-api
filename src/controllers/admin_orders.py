"""Super-only reading of every user's orders.

Separate from `order.py` because that one is scoped to the caller's own orders
by design: `/api/v1/orders` answers "my orders" for a machine caller and for the
dashboard alike. This one answers "everybody's orders", which is a different
question with a different audience, so it lives on the dashboard's own
unversioned surface behind `Dependencies.require_super` rather than widening a
machine route that every API key already reaches.

Read-only, like the rest of the order surface seen from a browser. Deciding what
happens to somebody else's order stays a CLI and owner-scoped operation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.schemas import OrderOut
from src.services import OrderError, OrderService


class AdminOrdersController:
  """Every order belonging to any user."""

  router = APIRouter(prefix="/admin", tags=["admin"])

  @router.get("/orders", response_model=list[OrderOut])
  def list_orders(_super=Depends(Dependencies.require_super),
                  db: Session = Depends(Dependencies.get_db)):
    """Every user's orders, newest first."""
    return [AdminOrdersController._out(order) for order in OrderService.list(db)]

  @router.get("/orders/{order_id}", response_model=OrderOut)
  def read_order(order_id: int, _super=Depends(Dependencies.require_super),
                 db: Session = Depends(Dependencies.get_db)):
    """One order, whoever it belongs to."""
    try:
      order = OrderService.get(db, order_id)
    except OrderError:
      # 404 rather than the 409 the mutating routes use: nothing is being
      # refused here, the order simply is not there.
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such order.")

    return AdminOrdersController._out(order)

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _out(order):
    """One order, with its owner's username joined in for the listing."""
    return {**order.as_dict(), "username": order.user.username if order.user else None}
