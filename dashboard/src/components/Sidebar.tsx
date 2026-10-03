import { NavLink } from 'react-router-dom'
import { BASENAME } from '../api/client'
import type { SessionUser } from '../api/types'
import { useI18n } from '../i18n/useI18n'
import type { MessageKey } from '../i18n/catalog/en'
import { NavIcon } from './NavIcon'
import type { NavIconName } from './NavIcon'

/** One destination in the sidebar. */
interface NavEntry {
  to: string
  label: MessageKey
  icon: NavIconName
}

/** Shared reference data, so it is everybody's. */
const CATALOGUE: NavEntry[] = [
  { to: '/products', label: 'nav.products', icon: 'products' },
  { to: '/shipping', label: 'nav.shipping', icon: 'shipping' },
]

/**
 * What one account owns: their orders, their recipients, their pages, and their
 * own API keys.
 *
 * API keys are here rather than under Administration because a key is the
 * caller's own credential, not something an administrator holds on their behalf —
 * every account mints and revokes its own without anyone else's permission.
 */
const WORK: NavEntry[] = [
  { to: '/orders', label: 'nav.orders', icon: 'orders' },
  { to: '/clients', label: 'nav.clients', icon: 'clients' },
  { to: '/pages', label: 'nav.pages', icon: 'pages' },
  { to: '/keys', label: 'nav.keys', icon: 'keys' },
]

/** The signed-in app's navigation.
 *
 * A sidebar rather than a bar because the list is seven deep and grows: down a
 * page it stays put, so the operator does not have to scroll back to it. Only the
 * destinations live here — who is signed in, and signing out, are in the menu at
 * the top right.
 *
 * Products, shipping, orders, clients, pages and API keys are linked for everybody.
 * The catalogue and the delivery prices are shared reference data, while an order,
 * a delivery recipient, a landing page and a user's own API keys each belong to
 * the user looking at them, so none is an administrator's privilege. Only Users is
 * admin-only, so a plain user does not see a page whose only outcome is a 403.
 *
 * **Every offset here is logical** — `start-0`, `ps-3`, `border-e` — because the
 * whole rail flips in Arabic. A literal `left-0` or `ml-2` here would leave the
 * active marker on the wrong side of every label in the other direction.
 */
export function Sidebar({
  user,
  onNavigate,
}: {
  user: SessionUser
  /** Called after a link is followed, so the mobile drawer closes behind it. */
  onNavigate(): void
}) {
  const { t } = useI18n()

  return (
    <div className="flex h-full flex-col bg-surface">
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
      <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-line px-5">
        <img
          src={`${BASENAME}/logo.png`}
          alt=""
          width={24}
          height={24}
          className="h-6 w-auto max-w-28 flex-none rounded object-contain"
        />
        <span className="truncate text-sm font-semibold tracking-tight">
          {t('nav.brand')}
          <span className="font-normal text-muted"> {t('nav.brandSuffix')}</span>
        </span>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        <NavGroup entries={CATALOGUE} onNavigate={onNavigate} />
        <NavGroup label={t('nav.workspace')} entries={WORK} onNavigate={onNavigate} />

        {user.is_admin ? (
          <NavGroup
            label={t('nav.administration')}
            entries={ADMIN}
            onNavigate={onNavigate}
          />
        ) : null}
      </nav>
    </div>
  )
}

const ADMIN: NavEntry[] = [{ to: '/users', label: 'nav.users', icon: 'users' }]

/** A titled run of links. The label is hidden from a screen reader: it describes
 * the group visually and the links below already say what they are.
 */
function NavGroup({
  label,
  entries,
  onNavigate,
}: {
  label?: string
  entries: NavEntry[]
  onNavigate(): void
}) {
  const { t } = useI18n()

  return (
    <div>
      {label ? (
        <p
          aria-hidden="true"
          className="mb-1.5 px-3 text-[0.6875rem] font-medium tracking-wider text-faint uppercase"
        >
          {label}
        </p>
      ) : null}

      <ul className="space-y-0.5">
        {entries.map((entry) => (
          <li key={entry.to}>
            <NavLink
              to={entry.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                [
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150',
                  isActive ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-raised hover:text-ink',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  {/*
                    The active item is marked by a bar as well as by colour.
                    Colour alone would leave a reader who cannot distinguish the
                    accent from the muted text with no way to tell where they are.
                  */}
                  <span
                    aria-hidden="true"
                    className={[
                      'absolute top-1/2 start-0 h-4 w-0.5 -translate-y-1/2 rounded-full transition-colors duration-150',
                      isActive ? 'bg-accent' : 'bg-transparent',
                    ].join(' ')}
                  />
                  <NavIcon
                    name={entry.icon}
                    className={[
                      'h-[1.125rem] w-[1.125rem] flex-none transition-colors duration-150',
                      isActive ? 'text-accent' : 'text-faint group-hover:text-muted',
                    ].join(' ')}
                  />
                  {t(entry.label)}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}
