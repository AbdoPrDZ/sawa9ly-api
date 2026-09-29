"""A user's own Telegram binding, over HTTP.

There is no route that binds somebody else's chat. A user links their own, and
there is deliberately no admin route for issuing a link on their behalf: a link
is the right to send messages into a chat, so letting an admin mint one is letting
an admin claim a user's notifications.

The poller is not a route either. It is a long-lived process — `python main.py
telegram listen` — for the same reason the tracking queue is not a route: one web
request should not be able to become a loop that outlives it.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import TelegramBindingError
from src.schemas import TelegramBindingOut, TelegramLinkOut
from src.services import TelegramService
from src.utils import TelegramError


class TelegramController:
  """Linking this user's account to a Telegram chat."""

  router = APIRouter(prefix="/telegram", tags=["telegram"])

  @router.get("", response_model=TelegramBindingOut)
  def binding(user=Depends(Dependencies.get_any_user),
              db: Session = Depends(Dependencies.get_db)):
    """Which chat this user's notifications go to, if any.

    Always answers, and reports an unbound account as `bound: false` rather than
    a 404: not having linked a chat is the normal state for most users, and the
    dashboard renders both from one shape.
    """
    return TelegramService.binding(db, user.username)

  @router.post("/link", response_model=TelegramLinkOut)
  def issue_link(user=Depends(Dependencies.get_any_user),
                 db: Session = Depends(Dependencies.get_db)):
    """A `t.me` link that binds this user's chat when opened.

    Returns a plaintext code once, in the URL. Only its hash is stored, so this
    is the only time it can be read — the same contract an API key has.

    Issuing a link does not unbind an existing chat. A user who asks for a second
    link and never opens it keeps the chat they had, so a mistake here cannot cost
    them a working binding.
    """
    try:
      return TelegramService.issue_link(db, user.username)
    except TelegramBindingError as error:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
      ) from error
    except TelegramError as error:
      # Telegram is unreachable. That is the site being broken, not the caller's
      # request being wrong, so it is a 502 rather than a 4xx.
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)
      ) from error

  @router.post("/test", response_model=dict)
  def send_test(user=Depends(Dependencies.get_any_user),
                db: Session = Depends(Dependencies.get_db)):
    """Send a test message to this user's own chat.

    The same operation as `python main.py telegram test`. It exists so the
    dashboard can check a link works without anyone opening a terminal, which is
    the point: the common case is a user clicking "did that work?".

    A 404 when no chat is linked, and a 502 when Telegram itself refuses — the
    first is this user's gap to close, the second is not.
    """
    try:
      sent = TelegramService.send_test(db, user.username)
    except TelegramBindingError as error:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
      ) from error
    except TelegramError as error:
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)
      ) from error

    return {"sent": True, "chat_id": sent["chat_id"]}

  @router.delete("", response_model=dict)
  def unbind(user=Depends(Dependencies.get_any_user),
             db: Session = Depends(Dependencies.get_db)):
    """Stop sending this user's notifications, and let them link a different chat."""
    if not TelegramService.unbind(db, user.username):
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No chat is linked to this account.",
      )

    return {"unbound": user.username}
