"""A user's own Telegram binding, as MCP tools.

The four operations the HTTP API exposes under `/api/v1/telegram`.

There is no tool here that links somebody else's chat, and there is no tool that
runs the poller. A link is the right to send messages into a chat, so issuing one
on another user's behalf would be claiming their notifications; and the poller is
a process — `python main.py telegram listen` — for the same reason the tracking
queue is not a route.
"""

from src.db import session_scope
from src.mcp.auth import McpAuth
from src.mcp.errors import McpError
from src.services import TelegramService


class TelegramTools:
  """Linking the caller's account to a Telegram chat."""

  @staticmethod
  def get_telegram_binding():
    """Which chat the caller's notifications go to, if any.

    Always answers, and reports an unlinked account as `bound: false` rather than
    an error: not having linked a chat is the normal state for most users.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return TelegramService.binding(db, user.username)

  @staticmethod
  def issue_telegram_link():
    """A `t.me` link that binds the caller's chat when they open it.

    The answer holds the plaintext code once, in the URL. Only its hash is
    stored, so this is the only time it can be read — the same contract an API
    key has. Send it to whoever needs the chat linked.

    Issuing a link does not unbind an existing chat: a caller who asks for a
    second link and never opens it keeps the one they had.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return TelegramService.issue_link(db, user.username)

  @staticmethod
  def send_telegram_test():
    """Send a test message to the caller's own linked chat.

    The check for whether a link works, without waiting for something worth being
    told about. Needs `TELEGRAM_BOT_TOKEN` set on the server, or Telegram itself
    cannot be reached and the call fails.
    """
    user = McpAuth.user()

    with session_scope() as db:
      return {"sent": True, "chat_id": TelegramService.send_test(db, user.username)["chat_id"]}

  @staticmethod
  def unbind_telegram():
    """Stop sending the caller's notifications, so a different chat can be linked."""
    user = McpAuth.user()

    with session_scope() as db:
      if not TelegramService.unbind(db, user.username):
        raise McpError(f"No chat is linked to {user.username}.")

      return {"unbound": user.username}

  @staticmethod
  def tools():
    return (
      TelegramTools.get_telegram_binding,
      TelegramTools.issue_telegram_link,
      TelegramTools.send_telegram_test,
      TelegramTools.unbind_telegram,
    )
