"""A signed-in user's own API keys.

Separate from `admin_keys.py` because that controller is about keys *across*
accounts, and this one is about the caller's own. The split is the permission
model: a key is the caller's to mint or drop, and issuing one for somebody else
is a super-only act on a different path.

Both return the same `AdminApiKeyOut` shape and share one `_out`, so the
dashboard renders a single table whether it is showing the caller's keys or
everybody's. A second, narrower shape would have meant the same component
handling two different row types for no gain.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.dependencies import Dependencies
from src.models import ApiKey, User
from src.schemas import AdminApiKeyCreateIn, AdminApiKeyOut, Page


class ApiKeysController:
  """The caller's own API keys."""

  router = APIRouter(prefix="/keys", tags=["keys"])

  @router.get("", response_model=Page[AdminApiKeyOut])
  def list_keys(q: str | None = None, limit: int | None = None,
                offset: int | None = None,
                user=Depends(Dependencies.require_user),
                db: Session = Depends(Dependencies.get_db)):
    """Your own keys, in creation order. Nobody else's are reachable from here.

    `q` searches the key prefix and the label; `limit` and `offset` page the
    result. All three are optional, and passing none of them returns every row.
    """
    return ApiKey.page(db, user.id, limit=limit, offset=offset,
                       search=q).as_dict(lambda key: ApiKeysController._out(key, db))

  @router.post("", response_model=AdminApiKeyOut,
               status_code=status.HTTP_201_CREATED)
  def create_key(body: AdminApiKeyCreateIn,
                 user=Depends(Dependencies.require_user),
                 db: Session = Depends(Dependencies.get_db)):
    """Issue a key for yourself. The plaintext is in this response only.

    There is no user in the path and none in the body: the owner is whoever is
    signed in. That is the whole point of the route — a user should not need an
    administrator standing between them and their own credentials.

    It does mean an account with no dashboard password cannot use this, because
    it cannot sign in to reach it. Those are API-only accounts, and a super
    issues their key from `/api/admin/users/{id}/api-keys`.
    """
    return ApiKeysController._issue(db, user.id, body)

  @router.delete("/{key_id}")
  def revoke_key(key_id: int, user=Depends(Dependencies.require_user),
                 db: Session = Depends(Dependencies.get_db)):
    """Revoke one of your own keys.

    A key that belongs to somebody else is a 404 rather than a 403, the same as a
    key id that does not exist at all: this route should not be usable to find
    out which keys other people hold.
    """
    key = db.get(ApiKey, key_id)

    if key is None or key.user_id != user.id:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No such API key."
      )

    key.revoked = True
    db.commit()

    return {"revoked": key.prefix}

  # --- shaping --------------------------------------------------------

  @staticmethod
  def _issue(db, user_id, body):
    """Create a key for one user and shape it, plaintext included.

    Lives here rather than on the admin controller because this is the keys
    controller and both issuing routes are the same act against a different
    `user_id` — the only difference between them is a permission, and a
    permission is a `Depends`, not a second copy of the body handling. The
    `ValueError` is the model's own "unknown key type", and it becomes a 400
    rather than a 500 because the value came off the wire.
    """
    try:
      key, plaintext = ApiKey.create(
        db, user_id, label=body.label, expires_in_days=body.expires_in_days,
        key_type=body.type,
      )
    except ValueError as error:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
      ) from error

    return {**ApiKeysController._out(key, db), "key": plaintext}

  @staticmethod
  def _out(key, db):
    """One key, with its owner's username joined in for the listing.

    Lives here rather than on the admin controller because this is the keys
    controller: the admin listing is the wider view of the same resource, and
    `AdminKeysController` calls this rather than keeping a second copy of the
    shape that could drift from it.
    """
    user = db.get(User, key.user_id)

    return {
      "id": key.id,
      "user_id": key.user_id,
      "username": user.username if user else None,
      "prefix": key.prefix,
      "type": key.type,
      "label": key.label,
      "revoked": key.revoked,
      "usable": key.is_valid(),
      "created_at": str(key.created_at) if key.created_at else None,
      "last_used_at": str(key.last_used_at) if key.last_used_at else None,
      "expires_at": str(key.expires_at) if key.expires_at else None,
    }
