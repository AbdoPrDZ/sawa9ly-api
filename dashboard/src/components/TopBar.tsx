import { NavLink } from 'react-router-dom'
import { BASENAME } from '../api/client'
import type { SessionUser } from '../api/types'

/** The dashboard chrome: navigation and who is signed in.
 *
 * Products, orders, clients and pages are linked for everybody: the catalogue
 * is shared reference data, while an order, a delivery recipient and a landing
 * page each belong to the user looking at them, so none is an administrator's
 * privilege. The user and API-key pages are linked only for an administrator, so
 * a plain user does not see a page whose only outcome is a 403.
 */
export function TopBar({ user, onSignOut }: { user: SessionUser; onSignOut(): void }) {
  return (
    <header className="topbar">
      {/*
        The logo and favicon live in `dashboard/assets`, which Vite's publicDir
        copies to the root of the build, so they are served as
        `<basename>/logo.png` and `<basename>/favicon.ico`. The path is built
        from `BASENAME` — the constant that already has to agree with `base` in
        vite.config.ts and `DASHBOARD_BASE` on the server — rather than written
        out again, so there is no fourth place to keep in step.

        `alt` is empty on purpose: the wordmark beside it already names the
        product, so a screen reader has nothing to gain and something to repeat.
      */}
      <span className="brand">
        <img
          className="brand-logo"
          src={`${BASENAME}/logo.png`}
          alt=""
          width={20}
          height={20}
        />
        Sawa9ly API Dashboard
      </span>

      <nav>
        <NavLink to="/products">Products</NavLink>
        <NavLink to="/orders">Orders</NavLink>
        <NavLink to="/clients">Clients</NavLink>
        <NavLink to="/pages">Pages</NavLink>
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
