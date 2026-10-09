"""User entity."""

import re
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, utcnow

#: The technical store name's shape: lowercase letters and digits, single hyphens
#: between them, no leading or trailing hyphen. It is a URL segment, so anything
#: else — a space, an accent, an Arabic letter — would need encoding and would
#: make two different names look the same in a browser.
STORE_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


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
  # The public storefront. There are two names on purpose: `store_name` is what
  # the owner and their customers see, `store_slug` is the URL segment and is the
  # only unique one. Both are required together for a store to exist, which is
  # why a store with no products and no pages is still listed — the names are the
  # store.
  store_name: Mapped[str | None] = mapped_column(String(255), default=None)
  store_slug: Mapped[str | None] = mapped_column(
    String(64), unique=True, index=True, default=None,
  )
  # A base64 data URI, validated by `src.utils.store_logo`. The logo is optional.
  store_logo: Mapped[str | None] = mapped_column(Text, default=None)
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
  def all(cls, db, limit=None, offset=None, search=None):
    """Every user, ordered by username, optionally narrowed and paged.

    `search` matches the username. Nothing else is searched: an admin listing
    users is looking for a name, and the credentials and chats beside it are
    deliberately not matchable text.
    """
    from src.models.paging import Paging

    return list(db.execute(Paging.apply(cls._filtered(search), limit, offset)).scalars())

  @classmethod
  def page(cls, db, limit=None, offset=None, search=None):
    """One page of users, and the total before paging.

    Separate from `all` because `all` is what the CLI reads and it has to keep
    returning a plain list. Only the admin list route needs the count.
    """
    from src.models.paging import Paging

    return Paging.run(db, cls._filtered(search), limit, offset)

  @classmethod
  def _filtered(cls, search=None):
    """The select every list of users shares."""
    from src.utils.search import Search

    query = select(cls).order_by(cls.username)

    match = Search.match(Search.like(cls.username, search))

    if match is not None:
      query = query.where(match)

    return query

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

  # --- the public store ------------------------------------------------

  @classmethod
  def by_store_slug(cls, db, slug):
    """The user whose store is at this URL segment, or None."""
    return db.execute(
      select(cls).where(cls.store_slug == slug)
    ).scalar_one_or_none()

  @classmethod
  def _store_filtered(cls, search=None):
    """Every user with a store, optionally narrowed.

    A store is public only when both names are set, so the filter is on both —
    a half-filled store is not a store and must not appear in the directory.
    """
    from src.utils.search import Search

    query = (
      select(cls)
      .where(cls.store_name.isnot(None), cls.store_slug.isnot(None))
      .order_by(cls.store_name)
    )

    match = Search.match(
      Search.like(cls.store_name, search),
      Search.like(cls.store_slug, search),
    )

    if match is not None:
      query = query.where(match)

    return query

  @classmethod
  def stores(cls, db, limit=None, offset=None, search=None):
    """One page of public stores, and the total before paging."""
    from src.models.paging import Paging

    return Paging.run(db, cls._store_filtered(search), limit, offset)

  @staticmethod
  def is_valid_store_slug(value):
    """Whether a value may be used as a store's URL segment."""
    return bool(value) and STORE_SLUG.match(value) is not None

  def has_store(self):
    """Whether this user has a public store (both names set)."""
    return bool(self.store_name and self.store_slug)

  def set_store(self, db, name, slug, logo=None):
    """Create or update this user's store.

    Both names are required together: the display name is what the store is
    called, the slug is where it lives. `logo` is a data URI or None to clear it;
    an absent logo is not the same as a cleared one, so a caller doing a partial
    update passes the current value through.

    Raises:
        ValueError: If either name is missing, the slug is not URL-safe, or the
          slug is already another store's.
    """
    from src.utils.store_logo import StoreLogo

    name = (name or "").strip()
    slug = (slug or "").strip().lower()

    if not name:
      raise ValueError("A store needs a display name.")

    if not User.is_valid_store_slug(slug):
      raise ValueError(
        "The technical name may use only lowercase letters, digits and single "
        "hyphens, and cannot start or end with a hyphen."
      )

    existing = User.by_store_slug(db, slug)

    if existing is not None and existing.id != self.id:
      raise ValueError(f"The technical name '{slug}' is already taken.")

    self.store_name = name
    self.store_slug = slug
    self.store_logo = StoreLogo.clean(logo)
    db.commit()

    return self

  def clear_store(self, db):
    """Take this user's store down, keeping the account."""
    self.store_name = None
    self.store_slug = None
    self.store_logo = None
    db.commit()

    return self

  def update_store(self, db, name=None, slug=None, logo=None):
    """Apply a partial store change. None means "unchanged".

    This is the shape a PATCH wants: only the fields the caller sent move. An
    empty name and an empty slug together remove the store, which is how a user
    takes theirs down; anything else is set through `set_store` and validated
    there, so a half-filled store is refused rather than stored.
    """
    effective_name = self.store_name if name is None else name
    effective_slug = self.store_slug if slug is None else slug
    effective_logo = self.store_logo if logo is None else logo

    if not (effective_name or "").strip() and not (effective_slug or "").strip():
      return self.clear_store(db)

    return self.set_store(db, effective_name, effective_slug, effective_logo)

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

  # --- language -------------------------------------------------------

  def locale(self, db):
    """Which language this user reads, and is written to.

    Read from the settings store rather than a column, so a language can be
    added without a migration. Anything unrecognised falls back to the default
    rather than raising: a stored value can be wrong, and a wrong language is a
    rough edge rather than a reason to refuse to send somebody their stock
    alert.
    """
    from src.i18n import Locale
    from src.models.setting import LOCALE_KEY

    return Locale.of(self.setting(db, LOCALE_KEY))

  def set_locale(self, db, locale):
    """Remember this user's language.

    Raises:
        ValueError: If `locale` is not one of `Locale.ALL`. Rejected rather than
          silently defaulted, because this is the API accepting bad input, not a
          hand-edited row.
    """
    from src.i18n import Locale
    from src.models.setting import LOCALE_KEY

    if not Locale.is_valid(locale):
      raise ValueError(
        f"Unknown locale '{locale}'; expected one of {', '.join(Locale.ALL)}."
      )

    return self.set_setting(db, LOCALE_KEY, locale)

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
