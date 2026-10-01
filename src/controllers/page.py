"""Landing page endpoints.

A page belongs to a user, so every route here is scoped to the caller: this is
the signed-in user's own pages and nothing else. Auth is `get_any_user`, so an
API key or a dashboard token both work, the same as `/api/v1/orders` and
`/api/v1/clients` — the dashboard edits pages, and the CLI and the API drive the
same thing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.schemas import Page, PageCreateIn, PageOut, PageUpdateIn
from src.services import LandingPageService, PageError


class PageController:
  """The landing pages a user has written for the catalogue's products."""

  router = APIRouter(prefix="/pages", tags=["pages"])

  @staticmethod
  def _owned(db, page_id, user):
    """The page, if the caller owns it. 404 otherwise, like every other id here.

    A 404 rather than a 403 on purpose: whether the page exists is not something
    to confirm for somebody else's id.
    """
    from src.models import LandingPage

    page = LandingPage.get(db, page_id)

    if page is None or page.user_id != user.id:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such page")

    return page

  @staticmethod
  def _run(action, *args, **kwargs):
    try:
      return action(*args, **kwargs)
    except PageError as error:
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

  @router.get("", response_model=Page[PageOut])
  def list_pages(q: str | None = None, limit: int | None = None,
                 offset: int | None = None,
                 user=Depends(Dependencies.get_any_user),
                 db: Session = Depends(Dependencies.get_db)):
    """The caller's own pages, newest first.

    `q` searches the title and the product id; `limit` and `offset` page the
    result. All three are optional, and passing none of them returns every row.
    """
    from src.models import LandingPage as PageRow

    return PageRow.page(db, user_id=user.id, limit=limit, offset=offset,
                        search=q).as_dict(PageController._out)

  @router.post("", response_model=PageOut, status_code=status.HTTP_201_CREATED)
  def create(body: PageCreateIn, user=Depends(Dependencies.get_any_user),
             db: Session = Depends(Dependencies.get_db)):
    """Start a draft page for one of the catalogue's products."""
    return PageController._out(PageController._run(
      LandingPageService.create, db, user.username,
      product_id=body.product_id, title=body.title, html=body.html,
    ))

  @router.get("/{page_id}", response_model=PageOut)
  def read(page_id: int, user=Depends(Dependencies.get_any_user),
           db: Session = Depends(Dependencies.get_db)):
    return PageController._out(PageController._owned(db, page_id, user))

  @router.patch("/{page_id}", response_model=PageOut)
  def update(page_id: int, body: PageUpdateIn, user=Depends(Dependencies.get_any_user),
             db: Session = Depends(Dependencies.get_db)):
    """Change a page's title, markup or state. Absent fields are left alone."""
    PageController._owned(db, page_id, user)
    return PageController._out(PageController._run(
      LandingPageService.update, db, page_id,
      title=body.title, html=body.html, state=body.state,
    ))

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _out(page):
    """One page, with the product it is about joined in for the listing."""
    product = page.product
    return {
      **page.as_dict(),
      "sawa9ly_product_id": product.product_id if product else None,
      "product_title": product.title if product else None,
    }
