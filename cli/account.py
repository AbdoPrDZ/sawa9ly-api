"""CLI: users and API keys."""

from src.models import Role


class AccountCli:
  """`user` and `apikey` — who may use the client and how."""

  @staticmethod
  def register(commands):
    user = commands.add_parser('user', help="manage users")
    user_actions = user.add_subparsers(dest='action', required=True)

    add = user_actions.add_parser('add', help="add a user")
    add.add_argument('username')
    add.add_argument('--email', default=None, help="sawa9ly account email")
    add.add_argument('--password', default=None, help="sawa9ly account password")
    add.add_argument('--role', default=None, choices=list(Role.ALL),
                     help="dashboard role (default: user)")
    add.add_argument('--login-password', default=None,
                     help="dashboard login password (not the sawa9ly password)")

    user_actions.add_parser('list', help="list users")

    set_role = user_actions.add_parser('set-role', help="change a user's role")
    set_role.add_argument('username')
    set_role.add_argument('role', choices=list(Role.ALL))

    set_login = user_actions.add_parser(
      'set-login-password', help="set or clear a user's dashboard password"
    )
    set_login.add_argument('username')
    set_login.add_argument('password', nargs='?', default=None,
                           help="omit or pass an empty value to lock the account out")

    delete = user_actions.add_parser('delete', help="delete a user and all its data")
    delete.add_argument('username')

    apikey = commands.add_parser('apikey', help="manage API keys")
    key_actions = apikey.add_subparsers(dest='action', required=True)

    create = key_actions.add_parser('create', help="create a key for a user")
    create.add_argument('--user', help="the account the key is for; defaults to the super admin")
    create.add_argument('--label', default=None)
    create.add_argument('--expires-in-days', type=int, default=None)

    listing = key_actions.add_parser('list', help="list a user's keys")
    listing.add_argument('--user', help="the account to list for; defaults to the super admin")

    revoke = key_actions.add_parser('revoke', help="revoke a key by its prefix")
    revoke.add_argument('prefix')
    revoke.add_argument('--user', help="the account the key belongs to; defaults to the super admin")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.models import ApiKey, User

    with Cli.db() as db:
      if args.command == 'apikey':
        if args.action == 'create':
          user = Cli.user(db, args.user)
          key, plaintext = ApiKey.create(
            db, user.id, label=args.label, expires_in_days=args.expires_in_days
          )
          return {
            'key': plaintext,
            'prefix': key.prefix,
            'user': user.username,
            'note': 'Store this now; only its hash is kept.',
          }

        if args.action == 'list':
          user = Cli.user(db, args.user)
          return {
            'user': user.username,
            'keys': [
              {
                'prefix': key.prefix,
                'label': key.label,
                'revoked': key.revoked,
                'created_at': str(key.created_at),
                'last_used_at': str(key.last_used_at) if key.last_used_at else None,
                'expires_at': str(key.expires_at) if key.expires_at else None,
              }
              for key in ApiKey.all(db, user.id)
            ],
          }

        if args.action == 'revoke':
          user = Cli.user(db, args.user)
          match = next(
            (key for key in ApiKey.all(db, user.id) if key.prefix == args.prefix), None
          )
          if match is None:
            raise SystemExit(f"error: no key with prefix '{args.prefix}' for '{args.user}'")
          match.revoked = True
          db.commit()
          return {'revoked': match.prefix, 'user': user.username}

      if args.action == 'add':
        if User.get(db, args.username) is not None:
          raise SystemExit(f"error: user '{args.username}' already exists")

        # An administrator that cannot sign in is worse than no administrator:
        # it looks like the dashboard is broken. This applies to `super` too.
        if args.role in Role.ADMINISTRATORS and not args.login_password:
          raise SystemExit(
            f"error: a '{args.role}' needs a dashboard password to sign in; "
            f"add --login-password (see: user add {args.username} --role "
            f"{args.role} --login-password ...)"
          )

        user = User.get_or_create(
          db, args.username, sawa9ly_email=args.email,
          sawa9ly_password=args.password, role=args.role,
        )

        if args.login_password:
          user.set_password(db, args.login_password)

        return AccountCli._user_row(user, db)

      if args.action == 'set-role':
        user = Cli.user(db, args.username)
        user.set_role(db, args.role)
        return {'username': user.username, 'role': user.role}

      if args.action == 'set-login-password':
        user = Cli.user(db, args.username)
        user.set_password(db, args.password)
        return {
          'username': user.username,
          'can_log_in': user.can_log_in(),
          'note': (
            'Dashboard password cleared; the user can no longer sign in.'
            if not user.can_log_in() else
            'Dashboard password set.'
          ),
        }

      if args.action == 'list':
        return {'users': [AccountCli._user_row(user, db) for user in User.all(db)]}

      if args.action == 'delete':
        if not User.delete(db, args.username):
          raise SystemExit(f"error: no user named '{args.username}'")
        return {'deleted': args.username}

  @staticmethod
  def _user_row(user, db):
    """One user as the CLI reports it."""
    from src.models import ApiKey

    return {
      'username': user.username,
      'id': user.id,
      'email': user.sawa9ly_email,
      'role': user.role,
      'can_log_in': user.can_log_in(),
      'api_keys': len(user.api_keys),
      'active_api_keys': sum(1 for key in user.api_keys if key.is_valid()),
      'clients': len(user.clients),
      'orders': len(user.orders),
      'created_at': str(user.created_at),
    }
