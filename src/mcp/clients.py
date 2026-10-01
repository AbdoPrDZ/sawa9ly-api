"""Delivery recipients, as MCP tools.

The three operations the HTTP API exposes under `/api/v1/clients`. A client is
one of the rows an order is addressed to, so everything here is the caller's own:
each tool narrows to the user behind the key.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.models import Client


class ClientsTools:
  """The people the caller's orders are shipped to."""

  @staticmethod
  def list_clients(q: str = None, limit: int = None, offset: int = None):
    """The caller's own delivery recipients.

    `q` searches the name and the phone number; `limit` and `offset` page the
    result. Passing none of them returns every row.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return Client.page(db, user.id, limit=limit, offset=offset, search=q).as_dict(
        lambda client: client.as_dict()
      )

  @staticmethod
  def create_client(full_name: str, phone: str = None, adresse: str = None,
                    wilaya_id: int = None, commune_id: int = None, note: str = None):
    """Add a delivery recipient, or update the one with the same name.

    The name is the identity, so creating somebody who already exists edits that
    row rather than adding a second. `wilaya_id` and `commune_id` are the ids the
    site's own dropdowns use; the site needs them to accept the order form.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return Client.get_or_create(
        db, user.id, full_name, phone=phone, adresse=adresse,
        wilaya_id=wilaya_id, commune_id=commune_id, note=note,
      ).as_dict()

  @staticmethod
  def get_client(client_id: int):
    """One delivery recipient, by id.

    Somebody else's is reported as absent rather than forbidden: whether the row
    exists is not this caller's business.
    """
    user = McpAuth.user()

    with session_scope() as db:
      client = Client.get(db, client_id)

      if client is None or client.user_id != user.id:
        raise McpError(f"No such client: {client_id}")

      return client.as_dict()

  @staticmethod
  def tools():
    return (
      ClientsTools.list_clients,
      ClientsTools.create_client,
      ClientsTools.get_client,
    )
