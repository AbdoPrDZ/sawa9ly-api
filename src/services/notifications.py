"""Turning something the queue noticed into a notification.

This module decides *what happened, in whose language, and who should hear about
it*. It does not send anything: it creates a `Notification`, and creating one is
what sends it. The reasoning for that is in `src/models/notification.py` — the
short version is that a message which was never recorded cannot be accounted for.

So the split is:

- this file — an event, the wording, and the set of people watching;
- `Notification.create` — the row, and the fan-out that goes with it;
- `NotificationDelivery.deliver` — the one place a message is put on its way.

What lives here is the wording, and the judgement about which changes are worth
raising at all. Adding a second kind of change means adding a line here and adding
its field to `NOTIFIABLE_FIELDS`; it does not mean touching delivery. The wording
itself lives in `src/i18n.py` so that the dashboard can be translated from the
same keys, and this module never holds a sentence of its own.

**One event, one row per language.** A `Notification` holds one title and one
body, and its docstring is explicit that the body is the verbatim record of what
went out. That is incompatible with a single row for an event whose watchers read
different languages: there would be three different texts and one place to keep
them. So the watchers are grouped by language and each group gets its own row,
with the text its readers will actually receive.

That keeps every existing property intact — one event still produces rows that
each carry exactly the text that was sent, `Notification.for_user` still answers
"what was I told", and a failed delivery is still retryable on its own. The only
thing that changed is the count: an event reaching three languages is three rows
rather than one. Nothing downstream de-duplicates on `Notification`, so that is
safe — and `latest_for`, the one method that could have, is not called from
anywhere.
"""

import logging

from src.i18n import Locale, Messages
from src.models import Notification, Product

logger = logging.getLogger(__name__)

#: Where a product lives, for the link at the end of a message.
PRODUCT_URL = "https://sawa9ly.app/product/{product_id}"

#: A product title can be very long and there is no reason for a chat message to
#: carry all of it. It is a limit on the site's own words, so it is the same in
#: every language.
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

    **And one per language on top of that**: watchers are grouped by the
    language they read, and each group is sent a message written in it. Every
    notification this returns is one row; a caller logging "the notification"
    should log the list.

    `previous` is what was stored before this fetch, which is what makes a change
    a change: a price of 16,000 is news only against a known different 16,000.

    Returns the list of `Notification` rows, empty when nothing worth sending
    changed or nobody is watching. An event with no audience is not a
    notification, and writing an empty row would be a record of nothing.
    """
    fields = [f for f in NOTIFIABLE_FIELDS if f in changed_fields]

    if not fields:
      return []

    groups = Notifications._watchers_by_locale(db, trackers)

    if not groups:
      return []

    rows = []

    for locale, user_ids in groups.items():
      lines = [Notifications._line(field, product, previous, locale) for field in fields]
      lines = [line for line in lines if line]

      if not lines:
        continue

      title, body = Notifications._text(product, lines, locale)

      row = Notification.create(
        db,
        kind=Notification.KIND_PRODUCT_CHANGED,
        title=title,
        body=body,
        user_ids=user_ids,
        product_id=product.id,
        bot=bot,
      )

      rows.append(row)

      for delivery in row.undelivered:
        logger.info(
          "  not delivered to user %s [%s]: %s",
          delivery.user_id, locale, delivery.send_error,
        )

    if rows:
      logger.info(
        "product %s changed (%s): told %s of %s watcher(s) in %s language(s)",
        product.product_id, ", ".join(fields),
        sum(row.sent for row in rows), sum(len(r.deliveries) for r in rows),
        len(rows),
      )

    return rows

  # --- the lines ------------------------------------------------------

  @staticmethod
  def _line(field, product, previous, locale):
    """The headline and detail for one changed field, or None if it did not.

    A field can be in the diff and still be nothing: the scan compares display
    text, and a price printed `16.000` this minute and `16,000` the next is the
    same price. That check happens here, where the two texts are to hand, so a
    reformat does not become a message about a comma.
    """
    if field == "available":
      return Notifications._availability_line(product, previous.get("available"), locale)

    if field == "price":
      return Notifications._price_line(product, previous.get("price"), locale)

    return None

  @staticmethod
  def _availability_line(product, was_available, locale):
    """In stock or out, and which way it went.

    Saying "availability changed" is not news; "it is gone" is.
    """
    if was_available is None:
      key = "product.available"
      detail = "product.available.detail"
    elif was_available:
      key = "product.unavailable"
      detail = "product.unavailable.detail"
    else:
      key = "product.available_again"
      detail = "product.available_again.detail"

    return (
      Messages.get(f"{key}.headline", locale, id=product.product_id),
      Messages.get(detail, locale),
    )

  @staticmethod
  def _price_line(product, was_text, locale):
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

    def say(key, **fields):
      return Messages.get(key, locale, **fields)

    def amount(value):
      return Locale.numbers(value, locale)

    if was is not None and now is not None:
      if now < was:
        headline = say("price.dropped.headline", now=amount(now))
      else:
        headline = say("price.rose.headline", now=amount(now))

      detail = say("price.was", was=amount(was))
    elif now is not None:
      headline = say("price.set.headline", now=amount(now))

      if was_text:
        detail = say("price.set.shown_before", previous=was_text)
      else:
        detail = say("price.set.never_shown")
    else:
      headline = say("price.gone.headline")

      if was is not None:
        detail = say("price.was", was=amount(was))
      else:
        detail = say("price.gone.never_numbered")

    return headline, detail

  # --- assembling -----------------------------------------------------

  @staticmethod
  def _text(product, lines, locale):
    """The headline and message for a set of changed fields.

    One change leads with its own headline, because "it is back in stock" is
    better than "something changed". More than one gets a neutral title and every
    change listed, so neither is buried.
    """
    if len(lines) == 1:
      title = lines[0][0]
    else:
      title = Messages.get("product.changed.title", locale, id=product.product_id)

    if len(lines) > 1:
      body_lines = [
        Messages.get("product.changed.intro", locale, id=product.product_id)
      ]
    else:
      body_lines = [lines[0][0]]

    for headline, detail in lines:
      body_lines.append("")
      body_lines.append(f"{headline}. {detail}" if len(lines) > 1 else detail)

    body_lines += [
      "",
      Notifications._title_of(product),
      "",
      PRODUCT_URL.format(product_id=product.product_id),
      "",
      Messages.get("product.watching_footer", locale),
    ]

    return title, "\n".join(body_lines)

  @staticmethod
  def _title_of(product):
    """The product's own title, shortened.

    The site's words, not ours, so there is nothing to translate — only to trim.
    The separator after the id in the framing above is a full stop, which reads
    the same in all three languages; the French `:` before a list is already in
    the translated string.
    """
    title = (product.title or "").strip()

    if not title:
      return f"Product {product.product_id}"

    return title[:TITLE_CHARS].rstrip() + ("…" if len(title) > TITLE_CHARS else "")

  # --- who ------------------------------------------------------------

  @staticmethod
  def _watchers(trackers):
    """The distinct users watching something, in a stable order.

    Deduplicated here as well as in `Notification.create`. Two watches on one
    product are one fact; a set of the same ids is what stops a second one
    becoming a second message, and returning them in insertion order keeps the
    deliveries reading the same way on every run.
    """
    return list(dict.fromkeys(tracker.user_id for tracker in trackers))

  @staticmethod
  def _watchers_by_locale(db, trackers):
    """Those watchers, grouped by the language each one reads.

    Ordered by `Locale.ALL` rather than by who happened to be first, so a run
    that finds the same watchers writes its notifications in the same order every
    time and the log lines line up.

    A watcher whose row has gone is skipped rather than treated as English: there
    is nobody left to send to, and a missing user is not a language.
    """
    from src.models import User

    groups: dict[str, list[int]] = {}

    for user_id in Notifications._watchers(trackers):
      user = User.get_by_id(db, user_id)

      if user is None:
        continue

      groups.setdefault(user.locale(db), []).append(user_id)

    return {
      locale: groups[locale]
      for locale in Locale.ALL
      if locale in groups
    }
