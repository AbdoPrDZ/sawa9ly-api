"""OrderLine entity: one product's quantity and price inside an order."""

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class OrderLine(Base):
  """A product on an order, with the quantity and unit price to sell it at.

  `price` is the reseller's selling price, which the website only keeps in the
  Livewire snapshot, so it is stored per order rather than on the cart.

  `note` is a remark about this one line — "gift wrap", "the blue one", "leave
  with the neighbour" — and is the only field here the site never sees. It is
  kept off the line deliberately: an order-level note and a line-level one are
  different things, and a line that says why it is priced oddly is worth
  recording without overwriting the order's own note.

  `origin_price` is the product's own cost **as it was when the line was
  created**, taken from the catalogue's `cost` and stored as a number. It is a
  snapshot on purpose: the site changes prices, and re-reading `product.cost`
  later would rewrite the history of every order that line is part of, so the
  margin an order was built at stops being recoverable. Once set it is never
  refreshed, not even when the line is topped up — a second purchase of the same
  product is a different moment and belongs in its own line if that moment
  matters.
  """

  __tablename__ = "order_lines"
  __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_line_order_product"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
  product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
  quantity: Mapped[int] = mapped_column(Integer, default=1)
  price: Mapped[int | None] = mapped_column(Integer, default=None)
  origin_price: Mapped[int | None] = mapped_column(Integer, default=None)
  note: Mapped[str | None] = mapped_column(Text, default=None)

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
      # The snapshot, not the product's current price. Reading the product here
      # would be the bug this column exists to prevent.
      'origin_price': self.origin_price,
      'subtotal': self.subtotal(),
      'title': self.product.title if self.product else None,
      'note': self.note,
    }

  def __repr__(self):
    return f"<OrderLine order={self.order_id} product={self.product_id} x{self.quantity}>"
