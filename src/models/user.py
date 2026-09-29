"""User entity."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow


class Role:
  """What a user is allowed to do.

  `super` is the root account, and is deliberately awkward to manage: the
  dashboard can neither create one nor change one, so a super cannot be
  promoted away or deleted by anyone working in the UI. It exists so there is
  always a way back in.

  `admin` manages users and API keys. `user` drives its own sawa9ly account and
  cannot see or change anything belonging to anyone else.
  """

  SUPER = "super"
  ADMIN = "admin"
  USER = "user"

  ALL = (SUPER, ADMIN, USER)
  DEFAULT = USER

  # Roles that may reach the admin routes at all.
  ADMINISTRATORS = (SUPER, ADMIN)

  @staticmethod
  def is_valid(role):
    return role in Role.ALL

  @staticmethod
  def can_administer(role):
    """Whether the role may reach the admin routes."""
    return role in Role.ADMINISTRATORS

  @staticmethod
  def is_super(role):
    return role == Role.SUPER

  @staticmethod
  def is_manageable_in_dashboard(role):
    """Whether the dashboard may set, change or delete a user of this role.

    `super` is excluded, which is the whole point of it: the UI cannot mint a
    second root account, and cannot demote or delete the one that exists. The
    environment and the CLI remain the only ways to manage a super.
    """
    return role in (Role.ADMIN, Role.USER)


class User(Base):
  """A sawa9ly account this client acts on behalf of.

  Each user keeps its own sawa9ly session, so two users never share a cart, and
  each carries its own `sawa9ly_email` / `sawa9ly_password`. There is no
  environment fallback: a user with no credentials recorded simply cannot sign
  in until they are given some, and `credentials()` says so.

  `password_hash` is unrelated to either of those: it is the password for
  signing in to the admin dashboard, and it is optional. A user without one
  cannot log in to the dashboard, whatever its role.
  """


  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  sawa9ly_email: Mapped[str | None] = mapped_column(String(255), default=None)
  sawa9ly_password: Mapped[str | None] = mapped_column(String(255), default=None)
  role: Mapped[str] = mapped_column(
    String(16), default=Role.DEFAULT, server_default=Role.DEFAULT, index=True,
  )
  password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

  settings: Mapped[list["Setting"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )
  api_keys: Mapped[list["ApiKey"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )
  clients: Mapped[list["Client"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )
  orders: Mapped[list["Order"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )
  landing_pages: Mapped[list["LandingPage"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )
  # One row per user, so this is a single object and not a list. `uselist=False`
  # is what tells SQLAlchemy that; without it every read of it is a list.
  telegram: Mapped["TelegramBinding | None"] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin", uselist=False,
  )
  notifications: Mapped[list["NotificationDelivery"]] = relationship(
    back_populates="user", cascade="all, delete-orphan", lazy="selectin",
  )

  # --- lookups ------------------------------------------------------

  @classmethod
  def get(cls, db, username):
    """Find a user by username, or None."""
    return db.execute(
      select(cls).where(cls.username == username)
    ).scalar_one_or_none()

  @classmethod
  def get_by_id(cls, db, user_id):
    """Find a user by primary key, or None."""
    return db.get(cls, user_id)

  @classmethod
  def get_or_create(cls, db, username, sawa9ly_email=None, sawa9ly_password=None,
                    inherit_credentials=True, role=None):
    """Return the named user, creating it when missing.

    Credentials on an existing user are only filled in when they are still
    empty, so re-running the CLI never overwrites what a server user was
    created with. Pass `inherit_credentials=False` for a user that must carry
    its own credentials and must never adopt another account's.

    `role` is applied only when the user is created. It is ignored on an
    existing user, because silently changing a role as a side effect of a
    lookup would be a nasty surprise; use `set_role` for that.
    """
    user = cls.get(db, username)

    if user is not None:
      if inherit_credentials:
        if sawa9ly_email and not user.sawa9ly_email:
          user.sawa9ly_email = sawa9ly_email
        if sawa9ly_password and not user.sawa9ly_password:
          user.sawa9ly_password = sawa9ly_password
        db.commit()

      return user

    user = cls(
      username=username,
      sawa9ly_email=sawa9ly_email,
      sawa9ly_password=sawa9ly_password,
      role=role or Role.DEFAULT,
    )
    db.add(user)
    db.commit()

    return user

  @classmethod
  def all(cls, db):
    """Every user, ordered by username."""
    return list(db.execute(select(cls).order_by(cls.username)).scalars())

  @classmethod
  def delete(cls, db, username):
    """Remove a user and everything hanging off it. True if one went."""
    user = cls.get(db, username)

    if user is None:
      return False

    db.delete(user)
    db.commit()

    return True

  @classmethod
  def admins(cls, db):
    """Every user who may administer others."""
    return list(
      db.execute(select(cls).where(cls.role == Role.ADMIN).order_by(cls.username)).scalars()
    )

  @classmethod
  def browsable(cls, db):
    """A username that can actually reach the site, or None.

    For the operations that read the site on behalf of *nobody in particular* —
    refreshing the catalogue, or a queue pass — where no user was named. It is
    never used to decide *whose* data to touch, only whose session to browse
    with, and there is no default preference: the first user by username with
    complete sawa9ly credentials wins, so the choice is deterministic rather
    than dependent on row order.

    Returns None when nobody has credentials, which the caller reports.
    """
    return db.execute(
      select(cls.username)
      .where(cls.sawa9ly_email.isnot(None), cls.sawa9ly_password.isnot(None))
      .order_by(cls.username)
      .limit(1)
    ).scalar_one_or_none()

  # --- role and dashboard password ------------------------------------

  def is_admin(self):
    """Whether this user may administer other users."""
    return Role.can_administer(self.role)

  def set_role(self, db, role):
    """Change this user's role.

    Raises:
        ValueError: If the role is not one of Role.ALL.
    """
    if not Role.is_valid(role):
      raise ValueError(f"Unknown role '{role}'; expected one of {', '.join(Role.ALL)}")

    self.role = role
    db.commit()

    return self

  def set_password(self, db, password):
    """Set the dashboard login password, hashing it.

    An empty password clears it, which locks the user out of the dashboard
    without touching their API keys.
    """
    from src.utils.passwords import Passwords

    self.password_hash = Passwords.hash(password) if password else None
    db.commit()

    return self

  def can_log_in(self):
    """Whether a dashboard login is possible at all for this user.

    A user with no password hash cannot be logged into, whatever its role.
    """
    return bool(self.password_hash)

  def check_password(self, password):
    """Whether the password is this user's dashboard password."""
    from src.utils.passwords import Passwords

    if not self.password_hash or not password:
      return False

    return Passwords.verify(password, self.password_hash)

  # --- settings -----------------------------------------------------

  def setting(self, db, key, default=None):
    """Read one of this user's settings."""
    from src.models.setting import Setting

    return Setting.get(db, self.id, key, default)

  def set_setting(self, db, key, value):
    """Create or update one of this user's settings."""
    from src.models.setting import Setting

    return Setting.set(db, self.id, key, value)

  def credentials(self):
    """This user's sawa9ly credentials.

    There is no environment fallback. Every user carries its own, because a
    fallback would let a user created for API access silently borrow the
    operator's account and its cart.

    Raises:
        LivewireError: If this user has no credentials recorded.
    """
    from src.utils.livewire import LivewireError

    if not self.sawa9ly_email or not self.sawa9ly_password:
      raise LivewireError(
        f"User '{self.username}' has no sawa9ly credentials. Record them with: "
        f"python main.py user add {self.username} --email <address> --password <password>"
      )

    return self.sawa9ly_email, self.sawa9ly_password

  def __repr__(self):
    return f"<User {self.username}>"
