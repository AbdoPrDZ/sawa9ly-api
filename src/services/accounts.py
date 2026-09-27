"""Account bootstrap and the rules around roles.

Two responsibilities, both about who is allowed to exist and who may change
whom, which is why they live together:

- ensuring a `super` account exists, from the environment, at startup;
- deciding what one role may do to another, so the dashboard does not have to
  re-derive the matrix in a route handler.

The super account is the recovery path. Once one exists it is left completely
alone: the environment will not reset its password and the dashboard cannot
create, promote, demote or delete it. A super is managed by editing the
environment or by hand, never from the UI.
"""

from src.config import Config
from src.db import session_scope
from src.models import Role, User


class AccountsError(RuntimeError):
  """The installation has no way in: no super account and nothing to make one."""


class Accounts:
  """Role rules, and the startup bootstrap for the super account."""

  # The environment variables that describe the super account are
  # Config.SUPER_ADMIN_USERNAME_VAR and Config.SUPER_ADMIN_PASSWORD_VAR. Both are
  # required: there is no fallback name or password, because a guessed default
  # for a root credential is not a default anyone wants.

  # --- startup bootstrap ----------------------------------------------

  @classmethod
  def bootstrap_super(cls):
    """Ensure a `super` user exists, creating it from the environment if not.

    Does nothing once any super exists, and does not touch an existing super's
    password — restarting the server must never invalidate a password the
    operator has since changed.

    Returns the username it acted on, or None if there was nothing to do.

    Raises:
        AccountsError: If no super exists and the environment does not provide
          the credentials to make one. The application cannot start in that
          state, because there would be no way to sign in at all.
    """
    # Called from the app factory, which has already done this, but bootstrap
    # has to be safe to call on its own against a brand new database.
    from src.utils.livewire import ensure_db

    ensure_db()

    with session_scope() as db:
      return cls._bootstrap_super(db)

  @classmethod
  def _bootstrap_super(cls, db):
    if cls.has_super(db):
      return None

    username = Config.super_username()
    password = Config.super_password()

    if not username or not password:
      raise AccountsError(cls._no_super_message())

    user = User.get(db, username)

    if user is None:
      user = User(username=username, role=Role.SUPER)
      db.add(user)
      db.commit()
    elif user.role != Role.SUPER:
      # The environment is declaring this account to be the root one, and
      # there is no other super to conflict with.
      user.role = Role.SUPER
      db.commit()

    user.set_password(db, password)

    return user.username

  @classmethod
  def _no_super_message(cls):
    """An error that says exactly what to do, since it stops the server."""
    return (
      "No 'super' user exists, and the environment does not define one, so "
      "there would be no way to sign in to the dashboard. Both of these must be "
      "set, and there is no default for either:\n"
      f"  {Config.SUPER_ADMIN_USERNAME_VAR}=<username>\n"
      f"  {Config.SUPER_ADMIN_PASSWORD_VAR}=<password>\n"
      "Or create the account by hand, which is then left alone on every "
      "startup:\n"
      f"  python main.py user add <username> --role {Role.SUPER} "
      "--login-password <password>"
    )

  @classmethod
  def has_super(cls, db):
    """Whether any super account exists.

    The check is "is there a super", not "does this named user exist", so a
    configured username never causes a second root account to be created.
    """
    return db.query(User).filter(User.role == Role.SUPER).first() is not None

  # --- role rules -----------------------------------------------------
  #
  # The matrix, in one place so a route handler never re-derives it:
  #
  #   actor \ action            self profile   create user   edit user   delete user
  #   super                     yes            yes           yes          yes
  #   admin                     yes            yes           no           no
  #   user                      yes            no            no           no
  #
  # Site credentials (the sawa9ly email and password) are super-only in every
  # case: a user edits their own through the profile page, and nobody else but a
  # super may write them on somebody's behalf.

  @classmethod
  def may_edit_profile(cls, actor, target):
    """Whether `actor` may edit `target` through the profile page.

    Always true for one's own account, at any role: a user has to be able to fix
    their own password and site credentials without an administrator involved.
    """
    return (True, "") if actor.id == target.id else (
      False, "You can only edit your own profile."
    )

  @classmethod
  def may_create_user(cls, actor):
    """Whether `actor` may add a user at all."""
    if not Role.can_administer(actor.role):
      return False, "This action needs an admin account."

    return True, ""

  @classmethod
  def may_set_role(cls, actor, role, target=None):
    """Whether `role` may be assigned, and to `target` when given.

    `super` is never assignable from the dashboard, by anyone: that would let an
    admin mint the account meant to be above them.
    """
    if not Role.can_administer(actor.role):
      return False, "This action needs an admin account."

    if not Role.is_manageable_in_dashboard(role):
      return False, (
        f"The '{role}' role cannot be assigned from the dashboard. Use "
        f"{Config.SUPER_ADMIN_USERNAME_VAR} / {Config.SUPER_ADMIN_PASSWORD_VAR}, or: "
        f"python main.py user set-role <username> {role}"
      )

    return True, ""

  @classmethod
  def may_set_site_credentials(cls, actor):
    """Whether `actor` may write a user's sawa9ly email or password for them.

    Super only. A user edits their own through the profile page; an admin
    creating a user cannot seed credentials on their behalf, so a newly added
    user starts with none and sets their own.
    """
    if not Role.is_super(actor.role):
      return False, (
        "Only a 'super' account can set another user's sawa9ly credentials. "
        "The user can add their own from their profile page."
      )

    return True, ""

  @classmethod
  def may_edit_user(cls, actor, target):
    """Whether `actor` may change `target` in the admin area.

    Super only. An administrator's job is adding users; changing existing ones
    is deliberately not part of it.
    """
    allowed, reason = cls._super_only(actor, "edit a user")

    if not allowed:
      return False, reason

    return cls._not_protected(actor, target)

  @classmethod
  def may_change_role(cls, actor, target, new_role):
    """Whether `actor` may put `target` into `new_role`."""
    allowed, reason = cls.may_edit_user(actor, target)

    if not allowed:
      return False, reason

    allowed, reason = cls.may_set_role(actor, new_role)

    if not allowed:
      return False, reason

    if target.id == actor.id and new_role != target.role:
      return False, "You cannot change your own role."

    return True, ""

  @classmethod
  def may_delete(cls, actor, target):
    """Whether `actor` may delete `target` and everything hanging off them."""
    allowed, reason = cls.may_edit_user(actor, target)

    if not allowed:
      return False, reason

    if target.id == actor.id:
      return False, "You cannot delete your own account."

    return True, ""

  @classmethod
  def _super_only(cls, actor, action):
    if not Role.is_super(actor.role):
      return False, f"Only a 'super' account can {action}."

    return True, ""

  @classmethod
  def _not_protected(cls, actor, target):
    """The shared check: is this target off limits to the dashboard at all?"""
    if not Role.is_manageable_in_dashboard(target.role):
      return False, (
        f"'{target.username}' has the '{target.role}' role, which the dashboard "
        "cannot change. Manage it from the environment or the CLI."
      )

    return True, ""
