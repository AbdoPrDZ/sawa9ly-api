"""Admin-only management of API keys, across every account.

Separate from `admin_users.py` because keys are a resource in their own right,
and a user is only ever a parameter here. Every route goes through
`Dependencies.require_admin`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import ApiKey, User
from src.schemas import AdminApiKeyCreateIn, AdminApiKeyOut


class AdminKeysController:
  """The API keys belonging to any user."""

  router = APIRouter(prefix="/admin", tags=["admin"])

  @router.get("/api-keys", response_model=list[AdminApiKeyOut])
  def list_keys(_admin=Depends(Dependencies.require_admin),
                db: Session = Depends(Dependencies.get_db)):
    """Every API key for every user."""
    return [AdminKeysController._out(key, db) for key in ApiKey.all(db)]

  @router.post("/users/{user_id}/api-keys", response_model=AdminApiKeyOut,
               status_code=status.HTTP_201_CREATED)
  def create_key(user_id: int, body: AdminApiKeyCreateIn,
                 _admin=Depends(Dependencies.require_admin),
                 db: Session = Depends(Dependencies.get_db)):
    """Issue a key for a user. The plaintext is in this response only."""
    user = db.get(User, user_id)

    if user is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No such user."
      )

    key, plaintext = ApiKey.create(
      db, user.id, label=body.label, expires_in_days=body.expires_in_days
    )

    return {**AdminKeysController._out(key, db), "key": plaintext}

  @router.delete("/api-keys/{key_id}")
  def revoke_key(key_id: int, _admin=Depends(Dependencies.require_admin),
                 db: Session = Depends(Dependencies.get_db)):
    """Revoke a key.

    Revocation is a flag rather than a delete, so the key stays visible as a
    record of what existed, and it takes effect on the key's next use.
    """
    key = db.get(ApiKey, key_id)

    if key is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No such API key."
      )

    key.revoked = True
    db.commit()

    return {"revoked": key.prefix}

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _out(key, db):
    """One key, with its owner's username joined in for the listing."""
    user = db.get(User, key.user_id)

    return {
      "id": key.id,
      "user_id": key.user_id,
      "username": user.username if user else None,
      "prefix": key.prefix,
      "label": key.label,
      "revoked": key.revoked,
      "usable": key.is_valid(),
      "created_at": str(key.created_at) if key.created_at else None,
      "last_used_at": str(key.last_used_at) if key.last_used_at else None,
      "expires_at": str(key.expires_at) if key.expires_at else None,
    }
