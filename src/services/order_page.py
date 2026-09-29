"""The site's order page, as a page model.

Sits beside `src/services/order.py` because the two are different things: that one
owns orders as the API and CLI understand them, this one knows how to read the
site's own rendering of one. This file is the only place that knows the page's
markup.

The structure it reads, all of it taken from a real order page rather than
guessed:

    h1                                    "#SW879988"     the site's reference
    h2  "حالة الطلب"                        order status
    h2  "منتجات"                            the order lines
    h2  "الملخص المالي"                      the financial summary
    h2  "زبون"                              the delivery details

and each line, a div holding:

    a[href$="/product/5663"]               the sawa9ly product id
    img[alt]                               the title
    span, "×", span                        unit price, then quantity
    .font-semibold span                    "= 14,500 دج", the base price
    .bg-red-500 span                       the line's status
    .bg-yellow-400                         the markup on the line

Two things about the base price are worth keeping in mind. It is the site's own
price for the product, so it is an independent check on a line's `origin_price`
rather than a copy of what we sent — the site would disagree if the product's
price moved after the order was placed. And the markup is simply the unit price
minus the base price, which is what the yellow badge shows; the two are read
separately so a disagreement is visible instead of being reconciled away.
"""

import logging
import re

from pyquery import PyQuery as pq

from src.utils import BASE_URL, Selector

logger = logging.getLogger(__name__)

#: The section headings the page is built from, as they appear in the markup.
#: Anchoring on them is what makes the sections separable: the page is a flat run
#: of Tailwind divs, so a section is "everything after this h2 until the next one".
#: If the site is ever translated these go with it, and `get_info` then finds no
#: sections rather than quietly returning an empty order.
CUSTOMER_HEADING = 'زبون'
LINES_HEADING = 'منتجات'
STATUS_HEADING = 'حالة الطلب'
SUMMARY_HEADING = 'الملخص المالي'

#: States the site has been observed to use, mapped to ours. Only words actually
#: seen appear here: an unrecognised one is passed through as `raw_status` and
#: left unmapped, because a wrong state is worse than an unread one.
STATUS_WORDS = {
  'ألغيت': 'cancelled',
  'قيد التنفيذ': 'processing',
}

#: The badge background each state is painted with. Used as a second opinion when
#: the wording is unfamiliar, and as the only signal when a badge has no text.
STATUS_COLOURS = {
  'bg-red-500': 'cancelled',
  'bg-green-500': 'delivered',
  'bg-blue-500': 'shipped',
  'bg-yellow-400': 'processing',
  'bg-emerald-500': 'confirmed',
}

#: Every state badge, whatever colour it is painted. The one selector that finds
#: a status on the page, so a new colour is visible here rather than invisible.
STATUS_BADGE = ','.join(f'div.{c}' for c in STATUS_COLOURS)

#: "The tracking number is not available yet" — the site saying it has none.
NO_TRACKING = 'غير متوفر'

#: A block holding one order line. The product link inside it is what makes a
#: block a line, so this is only a pre-filter.
LINE_BLOCK = 'div.flex.items-center.gap-3'

_MONEY = re.compile(r'-?[\d][\d\s.,]*')


class OrderPageError(Exception):
  """An order page cannot be read."""


class OrderPage(Selector):
  """One order on the site, read from its own page.

  Built per order because the url carries the id, and because a page is meant to
  be a thing you hold rather than a function you call with a document.
  """

  guide = {
    # The site's own reference, "#SW879988". The order number appears again in a
    # heading, but this is the one that is on the page as a title.
    "reference": "h1",
  }

  def __init__(self, origin_id, client):
    self.origin_id = int(origin_id)
    self.url = f"{BASE_URL}/order/{self.origin_id}"

    super().__init__(client)

  def get_info(self):
    """Scrape the order page.

    Returns:
        dict with the order's reference, status, delivery details, lines and
        financial summary. `lines` and `summary` are always present, empty when
        the page carries none.
    """
    if not self.select('reference'):
      raise OrderPageError(
        f"No order page came back for {self.origin_id}. If the session is stale, "
        f"refresh it with: python main.py login --user {self.client.username}"
      )

    raw = self._section_text(STATUS_HEADING)

    return {
      'origin_id': self.origin_id,
      'reference': self.select('reference').text().strip(),
      'status': self._status(raw),
      'raw_status': raw,
      'customer': self._customer(),
      'tracking': self._tracking(),
      'lines': self._lines(),
      'summary': self._summary(),
    }

  # --- sections -------------------------------------------------------

  def _section(self, heading):
    """The elements between a section heading and the next heading.

    Returns PyQuery objects, not the bare lxml elements iterating a selection
    hands back, so callers can keep selecting inside what they get back.
    """
    for element in self.doc('h2'):
      if OrderPage._text(element) != heading:
        continue

      found = []

      for sibling in element.itersiblings():
        # Another heading means the previous section ended, whether or not this
        # is the one after it.
        if sibling.tag in ('h1', 'h2'):
          break

        found.append(pq(sibling))

      return found

    return []

  def _section_text(self, heading):
    """A section's text with its labels dropped, leaving the values.

    The status section reads "حالة الطلب / ألغيت" once joined, and the words
    differ by section, so each one names what it wants rather than one rule
    trying to serve them all.
    """
    text = ' '.join(OrderPage._text(el) for el in self._section(heading))

    return text.replace(OrderPage._text_of(heading), '').strip()

  def _pairs(self, heading):
    """The label/value rows of a section, as a list of (label, value)."""
    pairs = []

    for element in self._section(heading):
      for row in self._each(element('div.flex.justify-between, div.flex.flex-col')):
        parts = [OrderPage._text(part) for part in row.children()]

        parts = [part for part in parts if part]

        if len(parts) == 2:
          pairs.append((parts[0], parts[1]))

    return pairs

  # --- status ---------------------------------------------------------

  def _status(self, raw):
    """Our name for a status, by its wording and then by its badge colour."""
    for word, name in STATUS_WORDS.items():
      if word in raw:
        return name

    for element in self._section(STATUS_HEADING):
      for badge in self._each(element(STATUS_BADGE)):
        classes = badge.attr('class') or ''

        for colour, name in STATUS_COLOURS.items():
          if colour in classes:
            return name

    return None

  def _tracking(self):
    """The site's tracking number, or None while it has none."""
    for label, value in self._pairs(STATUS_HEADING):
      if 'رقم التتبع' in label:
        return None if NO_TRACKING in value else value

    return None

  # --- details --------------------------------------------------------

  def _customer(self):
    """Where the order is going, as the site labels it."""
    return dict(self._pairs(CUSTOMER_HEADING))

  def _summary(self):
    """The financial summary, as label -> (text, amount).

    The amount is parsed out of the site's formatted money so it can be compared
    with ours; the text is kept because the Arabic label is the only thing that
    says which figure it was.
    """
    summary = {}

    for label, value in self._pairs(SUMMARY_HEADING):
      summary[label] = {'text': value, 'amount': OrderPage._amount(value)}

    return summary

  def _lines(self):
    """The order's lines.

    A block is a line when it links to a product, because that link is the only
    place the sawa9ly product id appears on the page — and it is the sawa9ly id
    that everything else is keyed on, never our internal one.
    """
    lines = []

    for element in self._section(LINES_HEADING):
      for block in self._each(element(LINE_BLOCK)):
        link = block('a[href*="/product/"]')

        if not len(link):
          continue

        match = re.search(r'/product/(\d+)', link.attr('href') or '')

        if not match:
          continue

        lines.append(self._line(block, link, int(match.group(1))))

        # The block has been read. Descending into it would find the same
        # product link again and report the line twice.
        break

    return lines

  def _line(self, block, link, product_id):
    """One order line, as the site shows it.

    `unit_price` is what was charged per unit, `base_price` is the site's own
    price for the product, and `markup` is the difference. All three are returned
    as the site printed them and as numbers, because a formatted string cannot be
    checked against ours and a number cannot be shown to a person.
    """
    words = self._line_words(block)
    badge = block('div.bg-yellow-400')
    markup = OrderPage._text(badge) if len(badge) else None
    unit = next((w for w in words if OrderPage._amount(w) is not None), None)
    quantity = next((w for w in words if w.isdigit()), None)
    base = OrderPage._base_price(words)

    return {
      'product_id': product_id,
      'title': OrderPage._text(link),
      'url': link.attr('href'),
      'image': block('img').attr('src') if len(block('img')) else None,
      'quantity': int(quantity) if quantity else None,
      'unit_price': OrderPage._amount(unit),
      'unit_price_text': unit,
      'base_price': OrderPage._amount(base),
      'base_price_text': base,
      'markup': OrderPage._amount(markup),
      'markup_text': markup,
      'status': self._line_status(block),
      'raw_status': self._raw_line_status(block),
    }

  @staticmethod
  def _base_price(words):
    """The "= 14,500 دج" word from a line's price row.

    Only the equals-marked word is taken. The row also holds the unit price and
    the quantity, and both parse as figures, so a fallback to "the last number in
    the row" would report a quantity of 2 as a base price of 2 — a small wrong
    number is worse here than no number, because it is the one field a caller has
    no other way to notice being wrong.

    Read from the price row rather than from a `.font-semibold` selector: the
    status badge and the markup badge in the same line carry that class too, so
    selecting on it returns the whole right-hand column of the line.
    """
    for word in words:
      if word.lstrip().startswith('=') and OrderPage._amount(word) is not None:
        return word

    return None

  def _line_words(self, block):
    """The short texts in a line's price row, in the order the page shows them.

    The row is "16,000 دج  ×  1  = 14,500 دج", so the price is first and the
    quantity is the one whole number in it.
    """
    row = block('.flex-grow .mt-2')

    if not len(row):
      row = block('.flex-grow')

    return [OrderPage._text(span) for span in row('span') if OrderPage._text(span)]

  def _raw_line_status(self, block):
    for badge in self._each(block(STATUS_BADGE)):
      for span in badge('span'):
        word = OrderPage._text(span)

        if word:
          return word

    return None

  def _line_status(self, block):
    """A line's state. A line can differ from its order, so it is read separately."""
    raw = self._raw_line_status(block)

    if raw:
      for word, name in STATUS_WORDS.items():
        if word in raw:
          return name

    classes = ' '.join((badge.attr('class') or '') for badge in self._each(block('div')))

    for colour, name in STATUS_COLOURS.items():
      if colour in classes:
        return name

    return None

  # --- text -----------------------------------------------------------

  @staticmethod
  def _each(selection):
    """Iterate a selection as PyQuery objects.

    Iterating a PyQuery selection hands back bare lxml elements, which cannot be
    selected from and answer `.attr` differently. Wrapping each one keeps the rest
    of this class working in a single style instead of guarding every call.
    """
    for element in selection:
      yield pq(element)

  @staticmethod
  def _text(node):
    """An element's text, whitespace collapsed.

    The markup is indented to suit the template, so raw text arrives with newlines
    and runs of spaces in it and cannot be compared to anything.

    Accepts a PyQuery object or a bare lxml element, because iterating a selection
    hands back the latter — and on those `.text` is the string rather than the
    method, so asking for `node.text()` raises.
    """
    raw = node.text_content() if hasattr(node, 'text_content') else node.text()

    return ' '.join((raw or '').split())

  @staticmethod
  def _text_of(value):
    return ' '.join(str(value).split())

  @staticmethod
  def _amount(text):
    """The number in a formatted price, or None.

    The site prints "16,000 دج". Both separator conventions are handled, because
    the site is Arabic and French-facing and either can be printed: in
    "1.250,00" the rightmost separator is the decimal point and the other is a
    thousands separator, and reading that as two decimal points turns 1250 into 1
    without raising.
    """
    if not text:
      return None

    match = _MONEY.search(str(text))

    if not match:
      return None

    return OrderPage._number(match.group(0).strip())

  @staticmethod
  def _number(token):
    """The figure in a numeric token, written either way round."""
    if ',' in token and '.' in token:
      # Two separators means one of them is the decimal point: the rightmost.
      if token.rindex(',') > token.rindex('.'):
        token = token.replace('.', '').replace(',', '.')
      else:
        token = token.replace(',', '')
    elif ',' in token or '.' in token:
      separator = ',' if ',' in token else '.'
      head, _, tail = token.rpartition(separator)

      # One separator followed by three digits is a thousands separator, as in
      # "16,000"; followed by one or two it is a decimal point, as in "1.5".
      token = f"{head}{tail}" if len(tail) == 3 else f"{head}.{tail}"

    try:
      return int(round(float(token)))
    except ValueError:
      return None
