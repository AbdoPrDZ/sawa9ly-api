"""Client endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.dependencies import Dependencies
from src.models import Client
from src.schemas import ClientIn, ClientOut


class ClientController:
  """The delivery recipients a user's orders are addressed to."""

  router = APIRouter(prefix="/clients", tags=["clients"])

  @staticmethod
  def _owned(db, client_id, user):
    client = Client.get(db, client_id)

    if client is None or client.user_id != user.id:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such client")

    return client

  @router.get("", response_model=list)
  def list_clients(user=Depends(Dependencies.get_current_user), db=Depends(Dependencies.get_db)):
    return [c.as_dict() for c in Client.all(db, user.id)]

  @router.post("", response_model=ClientOut)
  def create(body: ClientIn, user=Depends(Dependencies.get_current_user),
             db=Depends(Dependencies.get_db)):
    """Add a client, or update the one with the same name."""
    client = Client.get_or_create(
      db, user.id, body.full_name,
      phone=body.phone, adresse=body.adresse,
      wilaya_id=body.wilaya_id, commune_id=body.commune_id, note=body.note,
    )
    return client.as_dict()

  @router.get("/{client_id}", response_model=ClientOut)
  def read(client_id: int, user=Depends(Dependencies.get_current_user),
           db=Depends(Dependencies.get_db)):
    return ClientController._owned(db, client_id, user).as_dict()
