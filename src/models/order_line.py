"""OrderLine entity: one product's quantity and price inside an order."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class OrderLine(Base):
  """A product on an order, with the quantity and unit price to sell it at.

  `price` is the reseller's selling price, which the website only keeps in the
  Livewire snapshot, so it is stored per order rather than on the cart.
  """

  __tablename__ = "order_lines"
  __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_line_order_product"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
  product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
  quantity: Mapped[int] = mapped_column(Integer, default=1)
  price: Mapped[int | None] = mapped_column(Integer, default=None)

  order: Mapped["Order"] = relationship(back_populates="lines")
  product: Mapped["Product"] = relationship()

  @classmethod
  def get(cls, db, order_id, product_id):
    return db.execute(
      select(cls).where(cls.order_id == int(order_id), cls.product_id == int(product_id))
    ).scalar_one_or_none()

  def subtotal(self):
    """quantity * price, treating a missing price as zero."""
    return (self.price or 0) * (self.quantity or 0)

  def as_dict(self):
    return {
      'id': self.id,
      # The sawa9ly id, since that is what callers and the site use.
      'product_id': self.product.product_id if self.product else self.product_id,
      'quantity': self.quantity,
      'price': self.price,
      'subtotal': self.subtotal(),
      'title': self.product.title if self.product else None,
    }

  def __repr__(self):
    return f"<OrderLine order={self.order_id} product={self.product_id} x{self.quantity}>"
