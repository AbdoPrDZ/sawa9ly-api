"""Landing pages, as MCP tools.

The four operations the HTTP API exposes under `/api/v1/pages`. A page belongs
to a user, so every tool here is the caller's own and nothing else.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.models import LandingPage as PageRow
from src.services import LandingPageService


class PagesTools:
  """Landing pages written for the catalogue's products."""

  @staticmethod
  def list_pages(q: str = None, limit: int = None, offset: int = None):
    """The caller's own pages, newest first.

    `q` searches the title and the product id; `limit` and `offset` page the
    result. Passing none of them returns every row.

    Each row carries both product ids: `product_id` is ours, and
    `sawa9ly_product_id` is the one the site and the catalogue use. Only the
    second is worth passing back to `create_page`.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return PageRow.page(db, user_id=user.id, limit=limit, offset=offset,
                          search=q).as_dict(LandingPageService.describe)

  @staticmethod
  def create_page(product_id: int, title: str, html: str = ""):
    """Start a draft page for one of the catalogue's products.

    `product_id` is the sawa9ly id. Omit `html` for an empty page; it is the
    markup, not a file path.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return LandingPageService.describe(
        LandingPageService.create(db, user.username, product_id=product_id,
                                  title=title, html=html)
      )

  @staticmethod
  def get_page(page_id: int):
    """One page, with the product it is about."""
    user = McpAuth.user()

    with session_scope() as db:
      return LandingPageService.describe(PagesTools._owned(db, page_id, user.id))

  @staticmethod
  def update_page(page_id: int, title: str = None, html: str = None, state: str = None):
    """Change a page's title, markup or state. An absent field is left alone.

    `html` is the one to watch: passing an empty string clears the markup, which
    is not the same as leaving the key out. Only `publish` makes a page reachable
    at its public URL.
    """
    user = McpAuth.user()

    with session_scope() as db:
      PagesTools._owned(db, page_id, user.id)

      return LandingPageService.describe(
        LandingPageService.update(db, page_id, title=title, html=html, state=state)
      )

  @staticmethod
  def _owned(db, page_id, user_id):
    """The page, if the caller owns it. Otherwise absent, not forbidden."""
    page = PageRow.get(db, page_id)

    if page is None or page.user_id != user_id:
      raise McpError(f"No such page: {page_id}")

    return page

  @staticmethod
  def tools():
    return (
      PagesTools.list_pages,
      PagesTools.create_page,
      PagesTools.get_page,
      PagesTools.update_page,
    )
