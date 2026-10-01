"""The signed-in user: signing in, and their own account.

Profile routes are available to *any* signed-in user, whatever their role,
because a user must be able to fix their own password and their own sawa9ly
credentials without an administrator involved. Editing somebody else's account
is not here — that is `/api/admin`, and it is super-only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.schemas import LoginIn, ProfileIn, ProfileOut, Sawa9lyLoginOut, SessionOut
from src.services import Accounts
from src.utils.livewire import Livewire, LivewireError
from src.utils.tokens import Token


class AuthController:
  """Sign in, and manage your own account."""

  router = APIRouter(prefix="/auth", tags=["auth"])

  @staticmethod
  @router.post("/login", response_model=SessionOut)
  def login(body: LoginIn, db: Session = Depends(Dependencies.get_db)):
    """Sign in and return a token.

    A wrong username and a wrong password give the same answer on purpose:
    distinguishing them would tell an attacker which usernames exist.
    """
    from src.models import User

    user = User.get(db, body.username)

    if user is None or not user.check_password(body.password):
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Wrong username or password.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    return {
      "token": Token.issue(user, Token.signing_secret(db)),
      "token_type": "bearer",
      "expires_in": Token.TTL,
      "user": AuthController._who(user, db),
    }

  @staticmethod
  @router.get("/me")
  def me(user=Depends(Dependencies.get_token_user), db: Session = Depends(Dependencies.get_db)):
    """The signed-in user, or 401 if the token is missing, stale or expired."""
    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not signed in.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    return AuthController._who(user, db)

  @staticmethod
  @router.get("/me/profile", response_model=ProfileOut)
  def profile(user=Depends(Dependencies.get_token_user),
              db: Session = Depends(Dependencies.get_db)):
    """Your own account, including whether it can reach the site."""
    return AuthController._profile(user, db)

  @staticmethod
  @router.patch("/me/profile", response_model=ProfileOut)
  def update_profile(body: ProfileIn, user=Depends(Dependencies.get_token_user),
                     db: Session = Depends(Dependencies.get_db)):
    """Change your own dashboard password or sawa9ly credentials.

    Absent fields are left alone, so sending only `sawa9ly_email` does not wipe
    the password. Clearing a sawa9ly credential is done with an empty string,
    which is different from omitting it.
    """
    from src.models import User

    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not signed in.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    # Re-read: the token user is the same row, but this keeps the check honest
    # if the route is ever given a different subject.
    current = User.get_by_id(db, user.id)
    allowed, reason = Accounts.may_edit_profile(user, current)

    if not allowed:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    if body.sawa9ly_email is not None:
      current.sawa9ly_email = body.sawa9ly_email or None

    if body.sawa9ly_password is not None:
      current.sawa9ly_password = body.sawa9ly_password or None

    if body.password is not None:
      current.set_password(db, body.password)

    if body.locale is not None:
      # A 400 rather than a silent fallback: this is the API refusing a language
      # it does not speak, and quietly keeping the old one would leave the user
      # clicking a picker that did nothing.
      try:
        current.set_locale(db, body.locale)
      except ValueError as error:
        raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error

    db.commit()

    return AuthController._profile(current, db)

  @staticmethod
  @router.post("/me/sawa9ly-login", response_model=Sawa9lyLoginOut)
  def sawa9ly_login(user=Depends(Dependencies.get_token_user),
                    db: Session = Depends(Dependencies.get_db)):
    """Log in to sawa9ly for your own account, or refresh that session.

    This is the site login, not the dashboard one. It needs this user's stored
    sawa9ly credentials; without them there is nothing to log in with, and the
    message says so rather than failing obscurely.
    """
    from src.services import Cart

    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not signed in.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    if not (user.sawa9ly_email and user.sawa9ly_password):
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Add your sawa9ly email and password on your profile first.",
      )

    try:
      # Building the page client performs the site login when there is no live
      # session, and reuses the stored cookie when there is. One throwaway
      # Cart is enough to trigger it; the cart itself is not read.
      Cart(client=Livewire(user.username))
    except LivewireError as error:
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"The site rejected the login: {error}",
      ) from error

    return {
      "success": True,
      "username": user.username,
      "message": "Sawa9ly session ready.",
      "has_session": True,
    }

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _who(user, db):
    """The signed-in user, as the shell needs them.

    Read from the row rather than the token, so a demotion or a deleted account
    takes effect at once — and the language with it, since it lives on the user.
    """
    return {
      "id": user.id,
      "username": user.username,
      "role": user.role,
      "is_admin": user.is_admin(),
      "locale": user.locale(db),
    }

  @staticmethod
  def _profile(user, db):
    """The profile body, with the session status read from the stored settings."""
    from src.models import SESSION_KEY

    stored = user.setting(db, SESSION_KEY)

    return {
      "id": user.id,
      "username": user.username,
      "role": user.role,
      "is_admin": user.is_admin(),
      "can_log_in": user.can_log_in(),
      "has_sawa9ly_credentials": bool(user.sawa9ly_email and user.sawa9ly_password),
      "sawa9ly_email": user.sawa9ly_email,
      "has_sawa9ly_session": bool(stored),
      "locale": user.locale(db),
    }
