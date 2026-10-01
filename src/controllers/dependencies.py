"""Request plumbing: database sessions, API-key auth, admin tokens."""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.models import ApiKey, Role, User
from src.utils.tokens import Token
from src.utils.livewire import ensure_db


class Dependencies:
  """Callables the controllers depend on.

  Kept as classmethods so the whole request plumbing hangs off one
  namespace instead of a pile of module-level functions.
  """

  @staticmethod
  def get_db():
    """A database session for the request."""
    ensure_db()
    db = SessionLocal()

    try:
      yield db
    finally:
      db.close()

  @staticmethod
  def get_current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
  ):
    """Resolve the caller's user from an API key.

    Accepts the key via `X-API-Key` or a `Bearer` authorization header.
    """
    token = x_api_key

    if not token and authorization:
      scheme, _, value = authorization.partition(" ")
      if scheme.lower() == "bearer" and value:
        token = value.strip()

    if not token:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provide an API key via the X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    key = ApiKey.find(db, token)

    if key is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unknown API key.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    if not key.is_valid():
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="This API key has been revoked or has expired.",
      )

    key.touch()
    db.commit()

    return key.user

  @staticmethod
  def get_client(user: User = Depends(get_current_user)):
    """A Livewire client bound to the authenticated user.

    One is cached per user for the life of the process, because building one
    may log in — and each caller keeps their own sawa9ly session and cart.
    """
    from src.server import client_cache

    return client_cache(user.username)

  @staticmethod
  def get_cart(client=Depends(get_client)):
    from src.services import Cart

    return Cart(client=client)

  @staticmethod
  def get_product(product_id: int, client=Depends(get_client)):
    from src.services import Product

    return Product(product_id, client=client)

  # --- dashboard auth -------------------------------------------------

  @staticmethod
  def get_any_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
  ):
    """The caller, whether they presented an API key or a dashboard token.

    For resources both a machine and the dashboard need to reach, such as a
    user's own trackers. The token is tried first because a dashboard request
    always carries one, and it then falls back to the API key — both travel in
    the same `Authorization: Bearer` header, so the value has to be tried as
    each before either can be ruled out.

    401 when neither is valid, and deliberately not 403: a bad key and an expired
    token both mean "sign in again".
    """
    if not x_api_key:
      user = Dependencies.get_token_user(authorization, db)

      if user is not None:
        return user

    return Dependencies.get_current_user(x_api_key, authorization, db)

  @staticmethod
  def get_token_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
  ):
    """The user behind a dashboard token, or None.

    The user is always re-read from the database rather than trusted from the
    token payload, so a deleted user or a demoted admin loses access
    immediately instead of at token expiry.
    """
    token = Dependencies._bearer(authorization)

    if not token:
      return None

    payload = Token.verify(token, Token.signing_secret(db))

    if payload is None:
      return None

    return User.get_by_id(db, payload.get("sub"))

  @staticmethod
  def require_user(
    user=Depends(get_token_user),
  ):
    """A signed-in user of any role. A missing or stale token is a 401.

    The floor the self-service routes sit on. A user managing their own account —
    their profile, their keys — needs nothing beyond being signed in, so
    `require_admin` would be the wrong gate twice over: it would refuse a
    perfectly legitimate request, and it would make an ordinary account look
    like it lacked a permission it was never asking for.
    """
    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to the dashboard.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    return user

  @staticmethod
  def require_admin(
    user=Depends(get_token_user),
  ):
    """A signed-in admin. Anything less is a 401 or a 403.

    401 means "log in", 403 means "you are logged in, but not allowed". Keeping
    them apart is what lets the dashboard show the right message.
    """
    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to the dashboard.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    if not user.is_admin():
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This action needs an admin account.",
      )

    return user

  @staticmethod
  def require_super(
    user=Depends(get_token_user),
  ):
    """A signed-in `super`. Anything less is a 401 or a 403.

    The root role, for the handful of things an administrator must not reach:
    another user's orders, and site credentials on somebody's behalf. Same
    401/403 split as `require_admin`, so the dashboard can still tell "sign in"
    from "not allowed".
    """
    if user is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to the dashboard.",
        headers={"WWW-Authenticate": "Bearer"},
      )

    if not Role.is_super(user.role):
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This action needs a 'super' account.",
      )

    return user

  @staticmethod
  def _bearer(authorization):
    """Pull the token out of an `Authorization: Bearer ...` header."""
    if not authorization:
      return None

    scheme, _, value = authorization.partition(" ")

    if scheme.lower() != "bearer" or not value.strip():
      return None

    return value.strip()
