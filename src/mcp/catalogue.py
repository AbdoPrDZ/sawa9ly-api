"""The saved product catalogue, as MCP tools.

The three operations the HTTP API exposes under `/api/v1/catalogue`. A saved
product is one that has been scraped once and can then be read back without
costing another request to sawa9ly.app.

Unlike the catalogue routes they mirror, **every tool here requires a key**. That
is a deliberate divergence and it is worth stating plainly. The catalogue is
project-wide — the rows belong to no user, which is why the HTTP controller
carries no `Depends` and scrapes through whichever session
`User.browsable` picks. On a tool surface that reasoning inverts: a client that
can list the catalogue and trigger a scrape without presenting a credential is a
surface where nothing requires a credential, and the three tools that happen to
read local tables are the ones nobody would think to guard.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.models import Product as ProductRow
from src.services import Product as ProductPage


class CatalogueTools:
  """Scraping a product once, then serving it from the database."""

  @staticmethod
  def list_catalogue(q: str = None, limit: int = None, offset: int = None):
    """Every saved product, newest id last. Free: nothing is fetched.

    `q` searches the sawa9ly id and the title; `limit` and `offset` page the
    result. Passing none of them returns every row.
    """
    McpAuth.user()  # The catalogue is shared; this is the tool's own credential.

    with session_scope() as db:
      return ProductRow.page(db, limit=limit, offset=offset, search=q).as_dict(
        lambda product: product.as_dict()
      )

  @staticmethod
  def get_catalogue_product(product_id: int):
    """One saved product, by its sawa9ly id.

    Saved means scraped. An id that was never scraped is an error rather than an
    empty result, because there is no partial answer to give.
    """
    McpAuth.user()  # As above: the rows are shared, the credential is still required.

    with session_scope() as db:
      product = ProductRow.get(db, product_id)

      if product is None:
        raise McpError(
          f"Product {product_id} is not saved. Call save_catalogue_product first, "
          "to scrape and store its page."
        )

      return product.as_dict()

  @staticmethod
  def save_catalogue_product(product_id: int):
    """Scrape a product page from sawa9ly.app and store the result.

    Costs one request to the site, and is the only tool here that does.

    The scrape uses the **caller's** own sawa9ly session, where the HTTP route
    borrows the first user by name with complete credentials. That is the one
    behavioural difference between this tool and `/api/v1/catalogue/{id}`, and it
    follows from the credential: this call knows whose session it is, so there is
    nothing left to borrow one for. A caller whose own credentials are missing
    gets told so by name, with the command to fix it, rather than silently being
    served by a stranger's session.
    """
    product = ProductPage(product_id, McpAuth.client())

    with session_scope() as db:
      return ProductRow.save(db, product_id, product.get_info()).as_dict()

  @staticmethod
  def set_catalogue_price(product_id: int, price: int):
    """Set a saved product's sell price, in whole dinars.

    The cost is the site's own price and is read-only; this changes only what the
    product is sold for. Free: it never reaches sawa9ly.app.
    """
    McpAuth.user()  # The catalogue is shared; this is the tool's own credential.

    with session_scope() as db:
      product = ProductRow.get(db, product_id)

      if product is None:
        raise McpError(
          f"Product {product_id} is not saved. Call save_catalogue_product first, "
          "to scrape and store its page."
        )

      return product.set_price(db, price).as_dict()

  @staticmethod
  def tools():
    return (
      CatalogueTools.list_catalogue,
      CatalogueTools.get_catalogue_product,
      CatalogueTools.save_catalogue_product,
      CatalogueTools.set_catalogue_price,
    )
