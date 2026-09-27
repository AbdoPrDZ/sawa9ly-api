import { NavLink } from 'react-router-dom'
import type { SessionUser } from '../api/types'

/** The dashboard chrome: navigation and who is signed in.
 *
 * Products is linked for everybody: the catalogue is shared reference data, not
 * per-user state, so anyone signed in can browse it. The user and API-key pages
 * are linked only for an administrator, so a plain user does not see a page
 * whose only outcome is a 403.
 */
export function TopBar({ user, onSignOut }: { user: SessionUser; onSignOut(): void }) {
  return (
    <header className="topbar">
      <span className="brand">sawa9ly admin</span>

      <nav>
        <NavLink to="/products">Products</NavLink>
        {user.is_admin ? (
          <>
            <NavLink to="/users">Users</NavLink>
            <NavLink to="/keys">API keys</NavLink>
          </>
        ) : null}
        <NavLink to="/profile">My profile</NavLink>
      </nav>

      <div className="who">
        <span>
          {user.username} · {user.role}
        </span>
        <button type="button" className="ghost" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </header>
  )
}
