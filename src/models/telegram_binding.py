"""TelegramBinding entity: the chat this user is reachable at.

A user is linked to a Telegram chat by proving they can post in it. The proof is
a single-use code: the dashboard shows a `t.me` link carrying it, the user opens
it, and the bot is handed the code. Whoever sends the code gets the binding, so it
is short-lived and stored hashed.

One row per user, and a row carries both halves of the lifecycle:

    issued      chat_id null, code_hash set, code_expires_at set
    verified    chat_id set, code_hash null, verified_at set

So issuing a new code and using it are the same row moving between two states,
which means there is never more than one outstanding code per user and nothing to
clean up. A user who is already bound can be re-bound: issuing a code leaves the
working binding in place, and only the successful verification replaces it — so a
code that is never used costs nothing.

The chat id is stored as text. A Telegram channel's is `-1001234567890`, and
keeping the string the API handed us avoids a class of sign and width problem for
no benefit.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, as_utc, utcnow

#: What may be bound. A private chat and a private channel only: a group is
#: shared with people who are not this user, and a notification meant for one
#: account landing in everybody's group chat is not this user's to send.
#:
#: Enforced here rather than at the call site so the rule is in one place, and
#: `UNIQUE(chat_id)` underneath makes it true even if something reaches the
#: database another way.
DELIVERABLE_CHAT_TYPES = ("private", "channel")

REJECTED_CHAT_TYPES = ("group", "supergroup")

#: The alphabet a code is drawn from. No `0`/`O`, `1`/`I` or `l`: this is read
#: off a screen and typed by hand, and the two spellings of the same looking
#: character are the whole failure mode.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

CODE_LENGTH = 10
"""Ten characters from 32 gives 2**50. Hashing is sha256 rather than scrypt
  because a code is single-use and expires in minutes, so a leaked row is dead
  before an offline attack on it is worth running — and scrypt's 50-100ms would
  make every inbound message a small way to tie up the listener."""


class TelegramBindingError(Exception):
  """A binding cannot be issued, verified or created."""


class TelegramBinding(Base):
  """One user's link to a Telegram chat."""

  __tablename__ = "telegram_bindings"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
  )
  # NULL means a code is outstanding and no chat is bound yet. Unique so one chat
  # cannot be claimed by two accounts, which is the same rule the dashboard
  # states in words.
  chat_id: Mapped[str | None] = mapped_column(String(64), unique=True, default=None, index=True)
  chat_type: Mapped[str | None] = mapped_column(String(16), default=None)
  chat_title: Mapped[str | None] = mapped_column(String(255), default=None)
  chat_username: Mapped[str | None] = mapped_column(String(64), default=None)
  code_hash: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
  code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
  verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

  user: Mapped["User"] = relationship(back_populates="telegram")

  # --- codes ----------------------------------------------------------

  @staticmethod
  def generate_code():
    """A fresh (plaintext, hashed) pair.

    The plaintext is returned once and never stored: it is shown to the user in a
    link and cannot be read back out afterwards. This is the same contract API
    keys have, for the same reason.
    """
    plaintext = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))

    return plaintext, TelegramBinding.hash_code(plaintext)

  @staticmethod
  def hash_code(code):
    """The digest a code is stored and looked up as.

    Normalised first, so a code that arrives with anything wrapped around it
    still matches what `issue` stored from a bare code. Without that, a user who
    copied theirs out of a backticked page would be told their code was unknown
    while looking at it.
    """
    normalised = TelegramBinding.normalise_code(code)

    if normalised is None:
      # Not a code at all. Hashing it anyway means it can never match a stored
      # digest, which is the right outcome: an unparseable code is simply unknown.
      normalised = str(code or "").strip().upper()

    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()

  @staticmethod
  def normalise_code(text):
    """The code in some message text, uppercased and cleaned, or None.

    Returns the code rather than a yes/no, so the thing that decides whether text
    holds a code and the thing that hands the code on cannot disagree — which is
    how a backticked code ends up checked leniently and then hashed strictly.

    Anything around the code is removed: quotes, backticks, spaces. A sentence
    containing one is still rejected, because stripping the words out of
    "my code is ABCD1234" would leave a 10-character match for the wrong reason —
    incidental text must not be able to bind a chat.
    """
    if not text:
      return None

    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()

    if len(cleaned) != CODE_LENGTH:
      return None

    if not all(c in CODE_ALPHABET for c in cleaned):
      return None

    return cleaned

  # --- lookups --------------------------------------------------------

  @classmethod
  def for_user(cls, db, user_id):
    """This user's row, or None."""
    return db.execute(
      select(cls).where(cls.user_id == int(user_id))
    ).scalar_one_or_none()

  @classmethod
  def for_chat(cls, db, chat_id):
    """Whichever account this chat is bound to, or None."""
    if chat_id is None:
      return None

    return db.execute(
      select(cls).where(cls.chat_id == str(chat_id))
    ).scalar_one_or_none()

  @classmethod
  def with_pending_code(cls, db):
    """Every user who has a code outstanding."""
    return list(
      db.execute(select(cls).where(cls.code_hash.isnot(None))).scalars()
    )

  # --- issuing --------------------------------------------------------

  @classmethod
  def issue(cls, db, user_id, ttl_seconds=None):
    """Give this user a fresh code and return it.

    An existing binding is left alone. Re-binding is a deliberate act, so a code
    that is issued and never used must not cost the user the chat they already
    have.

    Raises:
        TelegramBindingError: If the user does not exist.
    """
    from src.config import Config
    from src.models import User

    user = User.get_by_id(db, user_id)

    if user is None:
      raise TelegramBindingError(
        "That user no longer exists, so no code was issued."
      )

    ttl = Config.TELEGRAM_CODE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    plaintext, digest = cls.generate_code()

    row = cls.for_user(db, user_id)

    if row is None:
      row = cls(user_id=user.id)
      db.add(row)

    row.code_hash = digest
    row.code_expires_at = utcnow() + timedelta(seconds=ttl)
    db.commit()

    return plaintext, row

  @classmethod
  def verify(cls, db, code):
    """Consume a code and return the row it belongs to.

    The code is cleared whether or not it turns out to be usable, so a stale one
    cannot be retried and an expired one leaves nothing behind.

    Raises:
        TelegramBindingError: If the code is unknown, expired, or its chat is
          already bound to another account.
    """
    digest = cls.hash_code(code)

    # Looked up by digest, not compared. The digest is a one-way function, so
    # finding no row for it leaks nothing about the code, and the database does
    # the work an `hmac.compare_digest` loop would be there to make slow.
    row = db.execute(
      select(cls).where(cls.code_hash == digest)
    ).scalar_one_or_none()

    if row is None:
      raise TelegramBindingError("That code is not one we issued.")

    expired = row.code_expires_at is not None and cls._reached(row.code_expires_at)

    row.code_hash = None
    row.code_expires_at = None

    if expired:
      db.commit()
      raise TelegramBindingError("That code has expired. Ask for a new one.")

    return row

  # --- binding --------------------------------------------------------

  def bind(self, db, chat):
    """Point this row at a chat, replacing whatever it pointed at before.

    `chat` is what Telegram reports for the id — its `type`, `title` and
    `username` — read with `getChat` rather than taken from the message, so what
    is stored is Telegram's own account of the chat and not a message's claim.

    Raises:
        TelegramBindingError: If the chat is a group, or already belongs to
          another account.
    """
    chat_id = str(chat.get("id"))
    chat_type = chat.get("type") or ""

    if chat_type in REJECTED_CHAT_TYPES:
      raise TelegramBindingError(
        f"This is a {chat_type}, which this bot does not use. Use a private chat "
        f"with the bot, or a private channel you own."
      )

    if chat_type not in DELIVERABLE_CHAT_TYPES:
      raise TelegramBindingError(
        f"Telegram reports this chat as {chat_type!r}, which is not one this bot "
        f"can send to. Expected one of: {', '.join(DELIVERABLE_CHAT_TYPES)}."
      )

    existing = TelegramBinding.for_chat(db, chat_id)

    if existing is not None and existing.user_id != self.user_id:
      raise TelegramBindingError(
        "That chat is already linked to another account. Unlink it there first, "
        "or use a different chat."
      )

    self.chat_id = chat_id
    self.chat_type = chat_type
    self.chat_title = chat.get("title")
    self.chat_username = (chat.get("username") or "").lstrip("@") or None
    self.verified_at = utcnow()

    try:
      db.commit()
    except IntegrityError:
      # The unique constraint is the authority; a concurrent link beat us to it.
      db.rollback()
      raise TelegramBindingError(
        "That chat was linked to another account a moment ago. Use a different chat."
      ) from None

    return self

  def unbind(self, db):
    """Forget the chat, keeping the row so a new code has somewhere to go."""
    self.chat_id = None
    self.chat_type = None
    self.chat_title = None
    self.chat_username = None
    self.verified_at = None
    self.code_hash = None
    self.code_expires_at = None
    db.commit()

    return self

  @staticmethod
  def _reached(deadline, now=None):
    """Whether a deadline stored in the database has passed.

    `as_utc` is what makes the comparison possible at all — the column is naive
    and `utcnow` is aware — and it lives in `src/db.py` because every column in
    this project has the same problem.
    """
    if deadline is None:
      return True

    return as_utc(deadline) <= (now or utcnow())

  def code_expired(self, now=None):
    """Whether the outstanding code is no longer usable.

    A code with no deadline is treated as expired rather than as never expiring.
    The deadline is what makes a leaked code worthless, so a row that lost it is
    not one to trust.
    """
    if self.code_hash is None:
      return False

    return TelegramBinding._reached(self.code_expires_at, now)

  def is_bound(self):
    return self.chat_id is not None

  def as_dict(self):
    """The binding, with the code never included — it is not stored in the clear
    and must not appear in an API response."""
    return {
      'user_id': self.user_id,
      'bound': self.is_bound(),
      'chat_id': self.chat_id,
      'chat_type': self.chat_type,
      'chat_title': self.chat_title,
      'chat_username': self.chat_username,
      'code_pending': self.code_hash is not None,
      'code_expires_at': str(self.code_expires_at) if self.code_expires_at else None,
      'verified_at': str(self.verified_at) if self.verified_at else None,
      'created_at': str(self.created_at),
    }

  def __repr__(self):
    return f"<TelegramBinding user={self.user_id} chat={self.chat_id}>"
