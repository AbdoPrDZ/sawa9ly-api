import { useEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import type { SessionUser } from '../api/types'
import { useI18n } from '../i18n/useI18n'
import { NavIcon } from './NavIcon'
import { RoleBadge } from './RoleBadge'

/** The signed-in account, in the top right, with the two things you can do to it.
 *
 * A menu rather than a permanent block, because the only other thing it holds is
 * the sign-out button: an operator opening this most weeks does not need the
 * username and role in front of them at all times.
 *
 * Closes on Escape, on a click outside, and after a link is followed — the three
 * ways a menu is expected to go away. Without the last one the page would change
 * behind a panel still describing the old one.
 *
 * Anchored with `end-0` rather than `right-0`, so the panel hangs off the same
 * edge as the button in both directions.
 */
export function UserMenu({ user, onSignOut }: { user: SessionUser; onSignOut(): void }) {
  const [open, setOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)
  const { t } = useI18n()

  useEffect(() => {
    if (!open) return

    function onPointerDown(event: MouseEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="relative" ref={container}>
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full py-1 ps-1 pe-2 transition-colors duration-150 hover:bg-raised"
      >
        {/*
          The initials stand in for an avatar, and the name is beside them from
          `sm` up: the initials alone are not enough to tell two accounts apart
          on a machine somebody else may be using.
        */}
        <span
          aria-hidden="true"
          className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-[0.6875rem] font-semibold text-accent uppercase"
        >
          {user.username.slice(0, 2)}
        </span>
        <span className="hidden max-w-32 truncate text-sm font-medium sm:block">
          {user.username}
        </span>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className={[
            'h-3.5 w-3.5 text-faint transition-transform duration-150',
            open ? 'rotate-180' : '',
          ].join(' ')}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open ? (
        <div className="menu mt-2 animate-pop-in" role="menu">
          <div className="menu-head">
            <p className="truncate text-sm font-medium">{user.username}</p>
            <RoleBadge role={user.role} />
          </div>

          <NavLink
            to="/profile"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="menu-item"
          >
            <NavIcon name="profile" className="h-4 w-4 flex-none text-faint" />
            {t('menu.profile')}
          </NavLink>

          <button
            type="button"
            role="menuitem"
            onClick={onSignOut}
            className="menu-item menu-item-danger"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="h-4 w-4 flex-none"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="m16 17 5-5-5-5" />
              <path d="M21 12H9" />
            </svg>
            {t('menu.signOut')}
          </button>
        </div>
      ) : null}
    </div>
  )
}
