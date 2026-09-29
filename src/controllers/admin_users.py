"""Admin-only management of users.

Every route goes through `Dependencies.require_admin`. There is no user id in
the path for acting *as* someone — a route acts on a target user by id, never as
one.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import Role, User
from src.schemas import AdminUserCreateIn, AdminUserIn, AdminUserOut
from src.services import Accounts


class AdminUsersController:
  """The user accounts, seen across the whole installation."""

  router = APIRouter(prefix="/admin/users", tags=["admin"])

  @router.get("", response_model=list[AdminUserOut])
  def list_users(_admin=Depends(Dependencies.require_admin),
                 db: Session = Depends(Dependencies.get_db)):
    """Every user, with the counts the dashboard shows."""
    return [AdminUsersController._out(user) for user in User.all(db)]

  @router.post("", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
  def create_user(body: AdminUserCreateIn, admin=Depends(Dependencies.require_admin),
                  db: Session = Depends(Dependencies.get_db)):
    """Create a user.

    Any administrator may add a user, and may set the dashboard login password
    they need to sign in with. Neither may set the new user's sawa9ly
    credentials: those are the user's own to set, from their profile, and an
    administrator who could type them in could also act as that user on the site.

    A duplicate username is a 409 rather than a silent update: overwriting
    somebody because a name was typed twice is not a useful merge.
    """
    allowed, reason = Accounts.may_create_user(admin)

    if not allowed:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    allowed, reason = Accounts.may_set_role(admin, body.role or Role.DEFAULT)

    if not allowed:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    if User.get(db, body.username) is not None:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A user named '{body.username}' already exists.",
      )

    # No sawa9ly credentials here, deliberately: the new user sets their own.
    user = User.get_or_create(db, body.username, role=body.role)

    if body.password:
      user.set_password(db, body.password)

    return AdminUsersController._out(user)

  @router.patch("/{user_id}", response_model=AdminUserOut)
  def update_user(user_id: int, body: AdminUserIn,
                  admin=Depends(Dependencies.require_admin),
                  db: Session = Depends(Dependencies.get_db)):
    """Edit a user. A super only.

    An ordinary administrator may add users but not change them, so this whole
    route refuses a non-super. Self-service lives on the profile route, which any
    signed-in user may use for their own account.
    """
    user = AdminUsersController._user_or_404(db, user_id)

    if body.role is not None:
      if not Role.is_valid(body.role):
        raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail=f"Unknown role '{body.role}'; expected one of "
                 f"{', '.join(Role.ALL)}.",
        )

      allowed, reason = Accounts.may_change_role(admin, user, body.role)

      if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

      user.set_role(db, body.role)

    if body.password is not None:
      allowed, reason = Accounts.may_edit_user(admin, user)

      if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

      user.set_password(db, body.password)

    db.commit()

    return AdminUsersController._out(user)

  @router.delete("/{user_id}")
  def delete_user(user_id: int, admin=Depends(Dependencies.require_admin),
                  db: Session = Depends(Dependencies.get_db)):
    """Delete a user and everything hanging off it, API keys included."""
    user = AdminUsersController._user_or_404(db, user_id)
    allowed, reason = Accounts.may_delete(admin, user)

    if not allowed:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    username = user.username
    db.delete(user)
    db.commit()

    return {"deleted": username}

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _user_or_404(db, user_id):
    user = User.get_by_id(db, user_id)

    if user is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No such user."
      )

    return user

  @staticmethod
  def _out(user):
    """A user as the dashboard sees them.

    `can_be_managed` drives whether the UI offers Edit/Delete at all, so a
    non-super admin is not shown controls whose only outcome is a 403.

    The sawa9ly and Telegram values are reported as facts and not as content:
    an operator needs to know whether this account is set up, and has no business
    holding the address or the chat it is bound to. The user set both, and can
    see both, on their own profile.
    """
    return {
      "id": user.id,
      "username": user.username,
      "role": user.role,
      "is_admin": user.is_admin(),
      "can_be_managed": Role.is_manageable_in_dashboard(user.role),
      "has_sawa9ly_credentials": bool(user.sawa9ly_email and user.sawa9ly_password),
      "telegram_chat_id": user.telegram.chat_id if user.telegram else None,
      "can_log_in": user.can_log_in(),
      "active_api_keys": sum(1 for key in user.api_keys if key.is_valid()),
      "clients": len(user.clients),
      "orders": len(user.orders),
      "created_at": str(user.created_at) if user.created_at else None,
    }
