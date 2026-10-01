"""Landing page service: a user's own pages for the catalogue's products."""

from src.models import LandingPage, PageState, Product, User


class PageError(Exception):
  """Raised when a page cannot be created or changed."""


class LandingPageService:
  """The landing pages a user has written.

  Ownership is the whole rule here: every method that takes a `user_id` narrows
  to it, so nothing in this service can reach another user's pages. The
  controller repeats that check on the single-page routes, because a page id
  alone must not be enough to read one.
  """

  # --- reading --------------------------------------------------------

  @staticmethod
  def get(db, page_id):
    page = LandingPage.get(db, page_id)
    if page is None:
      raise PageError(f"No page with id {page_id}")
    return page

  @staticmethod
  def list(db, user_id, product_id=None, state=None):
    if state is not None and not PageState.is_valid(state):
      raise PageError(
        f"Unknown page state {state!r}. Expected one of: {', '.join(PageState.ALL)}."
      )
    return LandingPage.all(db, user_id, product_id, state)

  @staticmethod
  def describe(page):
    """One page as a dict, with the sawa9ly product it is about joined in.

    Kept here so every front end renders a page the same way, rather than each
    resolving `page.product` itself. The joined fields are the reason: a page's
    own `product_id` is our internal key, which a caller cannot act on, so a
    shape without the sawa9ly id next to it invites someone to use the wrong one.
    """
    product = page.product

    return {
      **page.as_dict(),
      "sawa9ly_product_id": product.product_id if product else None,
      "product_title": product.title if product else None,
    }

  # --- writing --------------------------------------------------------

  @staticmethod
  def create(db, username, product_id, title, html=""):
    """Start a draft page for a user.

    `product_id` is the **sawa9ly** id, because that is the id the catalogue and
    the site use and therefore the one a caller has. It is translated to our own
    `products.id` here, and nowhere else may do that.
    """
    user = User.get(db, username)
    if user is None:
      raise PageError(f"No user named {username!r}")

    title = (title or "").strip()
    if not title:
      raise PageError("A page needs a title")

    # A product that is not saved yet gets a stub row, exactly as an order line
    # does, so a page can be written for a product before anyone scrapes it.
    product = Product.get_or_create(db, product_id)

    return LandingPage.create(db, user.id, product.id, title, html or "")

  @staticmethod
  def update(db, page_id, title=None, html=None, state=None):
    """Change a page. Absent fields are left alone."""
    page = LandingPageService.get(db, page_id)

    if title is not None:
      title = title.strip()
      if not title:
        raise PageError("A page needs a title")
      page.title = title

    if html is not None:
      page.html = html

    if state is not None:
      if not PageState.is_valid(state):
        raise PageError(
          f"Unknown page state {state!r}. Expected one of: {', '.join(PageState.ALL)}."
        )
      page.state = state

    db.commit()
    return page

  @staticmethod
  def set_state(db, page_id, state):
    """Move a page to another state."""
    return LandingPageService.update(db, page_id, state=state)

  # --- publishing -----------------------------------------------------

  @staticmethod
  def published(db, public_id):
    """The page a public request resolves to, or None.

    This is the only place `state` decides anything, and it is the whole reason
    the field exists: only a `publish` page is served. A `draft` or an `archive`
    is not found, and neither is one that was never published, so the public URL
    of an unpublished page leaks nothing — not that it exists.

    The shape check comes first so a request for `/favicon.ico` costs no query.
    """
    if not LandingPage.looks_like_public_id(public_id):
      return None

    page = LandingPage.get_by_public_id(db, public_id)

    if page is None or page.state != PageState.PUBLISH:
      return None

    return page
