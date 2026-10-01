"""Admin-only management of API keys, across every account.

Separate from `admin_users.py` because keys are a resource in their own right,
and a user is only ever a parameter here.

Two gates, not one. Reading and revoking across accounts is `require_admin`.
Issuing *for another user* is `require_super`: a key is a credential, and
handing somebody a credential in their name is a root-level act. A user issuing
a key for themselves is not on this controller at all — it is
`keys.py`, which is what lets an ordinary account manage its own keys without
any admin route being opened up to it.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.controllers.keys import ApiKeysController
from src.models import ApiKey, User
from src.schemas import AdminApiKeyCreateIn, AdminApiKeyOut, Page


class AdminKeysController:
  """The API keys belonging to any user."""

  router = APIRouter(prefix="/admin", tags=["admin"])

  @router.get("/api-keys", response_model=Page[AdminApiKeyOut])
  def list_keys(q: str | None = None, limit: int | None = None,
                offset: int | None = None,
                _admin=Depends(Dependencies.require_admin),
                db: Session = Depends(Dependencies.get_db)):
    """Every API key for every user.

    `q` searches the key prefix and the label; `limit` and `offset` page the
    result. All three are optional, and passing none of them returns every row.
    """
    return ApiKey.page(db, limit=limit, offset=offset, search=q).as_dict(
      lambda key: ApiKeysController._out(key, db)
    )

  @router.post("/users/{user_id}/api-keys", response_model=AdminApiKeyOut,
               status_code=status.HTTP_201_CREATED)
  def create_key(user_id: int, body: AdminApiKeyCreateIn,
                 superuser=Depends(Dependencies.require_super),
                 db: Session = Depends(Dependencies.get_db)):
    """Issue a key for another user. A `super` only.

    The plaintext is in this response only. This is the route an operator uses
    for an account that cannot sign in to the dashboard — one with no password,
    which by definition cannot reach `/api/keys` to issue its own.
    """
    user = db.get(User, user_id)

    if user is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No such user."
      )

    return ApiKeysController._issue(db, user.id, body)

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
