"""Order endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.schemas import OrderCheckoutIn, OrderCreateIn, OrderLineIn, OrderOut, Page
from src.services import OrderError, OrderService


class OrderController:
  """Building a draft order and submitting it to the site.

  Auth is `get_any_user`, so an API key or a dashboard token both work: the
  dashboard shows a user's own orders, and a machine drives them from the CLI.
  Widening the credential is safe here because every handler is scoped to
  `order.user_id == caller.id`, so neither credential reaches another user's
  orders.
  """

  router = APIRouter(prefix="/orders", tags=["orders"])

  @staticmethod
  def _owned(db, order_id, user):
    from src.models import Order

    order = Order.get(db, order_id)

    if order is None or order.user_id != user.id:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such order")

    return order

  @staticmethod
  def _run(action, *args, **kwargs):
    try:
      return action(*args, **kwargs)
    except OrderError as error:
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

  @router.get("", response_model=Page[OrderOut])
  def list_orders(q: str | None = None, limit: int | None = None,
                  offset: int | None = None,
                  user=Depends(Dependencies.get_any_user),
                  db=Depends(Dependencies.get_db)):
    """Your own orders, newest first.

    `q` searches the order id and the reference; `limit` and `offset` page the
    result. All three are optional, and passing none of them returns every row.
    """
    from src.models import Order as OrderRow

    return OrderRow.page(db, user_id=user.id, limit=limit, offset=offset,
                         search=q).as_dict(lambda o: o.as_dict())

  @router.post("", response_model=OrderOut)
  def create(body: OrderCreateIn, user=Depends(Dependencies.get_any_user),
             db=Depends(Dependencies.get_db)):
    """Start a draft order."""
    return OrderController._run(
      OrderService.create, db, user.username, client_id=body.client_id, note=body.note
    ).as_dict()

  @router.get("/{order_id}", response_model=OrderOut)
  def read(order_id: int, user=Depends(Dependencies.get_any_user),
           db=Depends(Dependencies.get_db)):
    return OrderController._owned(db, order_id, user).as_dict()

  @router.post("/{order_id}/lines", response_model=OrderOut)
  def add_line(order_id: int, body: OrderLineIn, user=Depends(Dependencies.get_any_user),
               db=Depends(Dependencies.get_db)):
    """Add a product to a draft order."""
    OrderController._owned(db, order_id, user)
    return OrderController._run(
      OrderService.add_line, db, order_id, body.product_id, body.quantity, body.price,
      body.note,
    ).as_dict()

  @router.delete("/{order_id}/lines/{product_id}", response_model=OrderOut)
  def remove_line(order_id: int, product_id: int, user=Depends(Dependencies.get_any_user),
                  db=Depends(Dependencies.get_db)):
    """Remove a product from a draft order."""
    OrderController._owned(db, order_id, user)
    return OrderController._run(
      OrderService.remove_line, db, order_id, product_id
    ).as_dict()

  @router.put("/{order_id}/lines/{product_id}/quantity", response_model=OrderOut)
  def set_quantity(order_id: int, product_id: int, body: OrderLineIn,
                  user=Depends(Dependencies.get_any_user), db=Depends(Dependencies.get_db)):
    """Set a draft order line's quantity."""
    OrderController._owned(db, order_id, user)
    return OrderController._run(
      OrderService.set_quantity, db, order_id, product_id, body.quantity
    ).as_dict()

  @router.put("/{order_id}/lines/{product_id}/price", response_model=OrderOut)
  def set_price(order_id: int, product_id: int, body: OrderLineIn,
                user=Depends(Dependencies.get_any_user), db=Depends(Dependencies.get_db)):
    """Set a draft order line's price."""
    OrderController._owned(db, order_id, user)
    return OrderController._run(
      OrderService.set_price, db, order_id, product_id, body.price
    ).as_dict()

  @router.post("/{order_id}/checkout", response_model=dict)
  def checkout(order_id: int, body: OrderCheckoutIn | None = None,
               user=Depends(Dependencies.get_any_user), db=Depends(Dependencies.get_db)):
    """Submit a draft order to the site: fill the cart, fill the form, submit.

    A successful submit confirms the order. Use `dry_run` to stage the cart
    without ordering.
    """
    OrderController._owned(db, order_id, user)
    dry_run = body.dry_run if body else False
    result = OrderController._run(
      OrderService.checkout, db, order_id, username=user.username, dry_run=dry_run
    )
    return result
