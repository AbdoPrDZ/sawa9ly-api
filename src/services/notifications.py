"""Turning something the queue noticed into a notification.

This module decides *what happened and who should hear about it*. It does not send
anything: it creates a `Notification`, and creating one is what sends it. The
reasoning for that is in `src/models/notification.py` — the short version is that a
message which was never recorded cannot be accounted for.

So the split is:

- this file — an event, a headline, the text, and the set of people watching;
- `Notification.create` — the row, and the fan-out that goes with it;
- `NotificationDelivery.deliver` — the one place a message is put on its way.

What lives here is the wording, and the judgement about which changes are worth
raising at all. Adding a second kind of change means adding a line here and adding
its field to `NOTIFIABLE_FIELDS`; it does not mean touching delivery.
"""

import logging

from src.models import Notification, Product

logger = logging.getLogger(__name__)

#: Where a product lives, for the link at the end of a message.
PRODUCT_URL = "https://sawa9ly.app/product/{product_id}"

#: A product title can be very long and there is no reason for a chat message to
#: carry all of it.
TITLE_CHARS = 80

#: The tracked fields that are worth a message, in the order they are listed in
#: one. Anything else a scan notices — a title edit, a new image, a description
#: change — is recorded in the diff and reported by the pass, but is not worth
#: interrupting somebody over. Written out rather than derived, because "is this
#: worth telling a person" is a judgement and a table would be a way of never
#: making it.
NOTIFIABLE_FIELDS = ("available", "price")


class Notifications:
  """Raising the news that the watchers asked for."""

  @staticmethod
  def product_changed(db, product, trackers, previous, changed_fields, bot=None):
    """Record that a watched product changed, and tell its watchers.

    **One notification per product per fetch, whatever changed.** A scrape that
    finds both the price and the stock different is one event that happened once,
    and sending two messages about it is the sort of thing that gets a bot muted.
    Each change gets its own line inside one message instead.

    `previous` is what was stored before this fetch, which is what makes a change
    a change: a price of 16,000 is news only against a known different 16,000.

    Returns the `Notification`, or None when nothing worth sending changed or
    nobody is watching. An event with no audience is not a notification, and
    writing an empty row would be a record of nothing.
    """
    fields = [f for f in NOTIFIABLE_FIELDS if f in changed_fields]

    if not fields:
      return None

    watchers = Notifications._watchers(trackers)

    if not watchers:
      return None

    lines = [Notifications._line(field, product, previous) for field in fields]
    lines = [line for line in lines if line]

    if not lines:
      return None

    title, body = Notifications._text(product, lines)

    row = Notification.create(
      db,
      kind=Notification.KIND_PRODUCT_CHANGED,
      title=title,
      body=body,
      user_ids=watchers,
      product_id=product.id,
      bot=bot,
    )

    logger.info(
      "product %s changed (%s): told %s of %s watcher(s)",
      product.product_id, ", ".join(fields), row.sent, len(watchers),
    )

    for delivery in row.undelivered:
      logger.info(
        "  not delivered to user %s: %s", delivery.user_id, delivery.send_error
      )

    return row

  # --- the lines ------------------------------------------------------

  @staticmethod
  def _line(field, product, previous):
    """The headline and detail for one changed field, or None if it did not.

    A field can be in the diff and still be nothing: the scan compares display
    text, and a price printed `16.000` this minute and `16,000` the next is the
    same price. That check happens here, where the two texts are to hand, so a
    reformat does not become a message about a comma.
    """
    if field == "available":
      return Notifications._availability_line(product, previous.get("available"))

    if field == "price":
      return Notifications._price_line(product, previous.get("price"))

    return None

  @staticmethod
  def _availability_line(product, was_available):
    """In stock or out, and which way it went.

    Saying "availability changed" is not news; "it is gone" is.
    """
    if was_available is None:
      headline = f"Product {product.product_id} is available"
      detail = "It was not known to be in stock before."
    elif was_available:
      headline = f"Product {product.product_id} is no longer available"
      detail = "It has gone out of stock."
    else:
      headline = f"Product {product.product_id} is available again"
      detail = "It is back in stock."

    return headline, detail

  @staticmethod
  def _price_line(product, was_text):
    """The price now, and what it was.

    Returns None when the two texts are the same number: the site is free to
    change how it formats a price without the price changing, and a message about
    a comma helps nobody.

    `None` is a value, not a gap. A price that disappears — "sur demande" — and
    one that comes back are both events, because for somebody reselling the
    product that is precisely the news.
    """
    was = Product.parse_price(was_text)
    now = Product.parse_price(product.price)

    if was == now:
      return None

    if was is not None and now is not None:
      if now < was:
        headline = f"Price dropped to {now:,}"
        detail = f"It was {was:,}."
      else:
        headline = f"Price went up to {now:,}"
        detail = f"It was {was:,}."
    elif now is not None:
      headline = f"Price is now {now:,}"
      detail = (
        f"It previously showed as {was_text}." if was_text
        else "It previously had no price shown."
      )
    else:
      headline = "No longer shows a price"
      detail = (
        f"It was {was:,}." if was is not None
        else "The site is no longer showing a number for it."
      )

    return headline, detail

  # --- assembling -----------------------------------------------------

  @staticmethod
  def _text(product, lines):
    """The headline and message for a set of changed fields.

    One change leads with its own headline, because "it is back in stock" is
    better than "something changed". More than one gets a neutral title and every
    change listed, so neither is buried.
    """
    if len(lines) == 1:
      title = lines[0][0]
    else:
      title = f"Product {product.product_id} changed"

    body_lines = [f"Product {product.product_id} changed:"] if len(lines) > 1 else [
      lines[0][0],
    ]

    for headline, detail in lines:
      body_lines.append("")
      body_lines.append(f"{headline}. {detail}" if len(lines) > 1 else detail)

    body_lines += [
      "",
      Notifications._title_of(product),
      "",
      PRODUCT_URL.format(product_id=product.product_id),
      "",
      "You are watching this product.",
    ]

    return title, "\n".join(body_lines)

  @staticmethod
  def _title_of(product):
    title = (product.title or "").strip()

    if not title:
      return f"Product {product.product_id}"

    return title[:TITLE_CHARS].rstrip() + ("…" if len(title) > TITLE_CHARS else "")

  @staticmethod
  def _watchers(trackers):
    """The distinct users watching something, in a stable order.

    Deduplicated here as well as in `Notification.create`. Two watches on one
    product are one fact; a set of the same ids is what stops a second one
    becoming a second message, and returning them in insertion order keeps the
    deliveries reading the same way on every run.
    """
    return list(dict.fromkeys(tracker.user_id for tracker in trackers))
