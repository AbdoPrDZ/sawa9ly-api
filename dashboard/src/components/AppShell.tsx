import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import type { SessionUser } from '../api/types'
import { useI18n } from '../i18n/useI18n'
import { Banner } from './Banner'
import { LanguageToggle } from './LanguageToggle'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'
import { UserMenu } from './UserMenu'

/** The signed-in layout: navigation down the side, the page beside it.
 *
 * Below `lg` the same sidebar becomes a drawer behind a hamburger, and the
 * navigation closes as soon as a destination is followed — otherwise it would
 * stay over the page the reader just asked for.
 */
export function AppShell({
  user,
  onSignOut,
  children,
}: {
  user: SessionUser
  onSignOut(): void
  children: ReactNode
}) {
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  const { t, direction, localeError } = useI18n()

  // A drawer is a modal surface: escape has to close it, or a keyboard user who
  // opened it is trapped behind it.
  useEffect(() => {
    if (!navOpen) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setNavOpen(false)
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [navOpen])

  return (
    <div className="min-h-screen">
      {/*
        One sidebar, not two. The drawer and the docked rail are the same element
        at different widths, so a link exists once in the document and a screen
        reader is not offered the navigation twice.

        `invisible` on the closed drawer keeps it out of the tab order while it
        sits off-screen; the transform alone would only move it.

        `start-0` is logical on purpose — the rail is pinned to the reading edge,
        so in Arabic it sits on the right. The off-screen transform is chosen by
        direction rather than layered with an `rtl:` override, because "off-screen"
        is the *opposite* side in each: a closed rail has to go further left in a
        left-to-right layout and further right in a right-to-left one.
      */}
      <aside
        className={[
          'fixed inset-y-0 start-0 z-40 w-64 border-e border-line',
          'transition-[transform,visibility] duration-200 ease-out lg:visible lg:translate-x-0',
          navOpen
            ? 'visible translate-x-0'
            : `invisible ${direction === 'rtl' ? 'translate-x-full' : '-translate-x-full'}`,
        ].join(' ')}
      >
        <Sidebar user={user} onNavigate={() => setNavOpen(false)} />
      </aside>

      {navOpen ? (
        <div
          role="presentation"
          onClick={() => setNavOpen(false)}
          className="fixed inset-0 z-30 animate-fade bg-black/60 lg:hidden"
        />
      ) : null}

      <div className="lg:ps-64">
        {/*
          The one bar above the page. At this width the sidebar holds the brand,
          so the bar carries only what it cannot: the way to open the sidebar
          below `lg`, the theme, and who is signed in.
        */}
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-canvas/80 px-4 backdrop-blur-sm sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setNavOpen(true)}
            aria-label={t('nav.open')}
            aria-expanded={navOpen}
            className="btn btn-ghost -ms-2 px-2 lg:hidden"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              aria-hidden="true"
              className="h-5 w-5"
            >
              <path d="M4 6h16" />
              <path d="M4 12h16" />
              <path d="M4 18h16" />
            </svg>
          </button>

          {/* The wordmark only below `lg`: from there up the sidebar already
              carries it, and saying it twice is noise. */}
          <span className="truncate text-sm font-semibold lg:hidden">{t('app.name')}</span>

          <div className="ms-auto flex items-center gap-1">
            <LanguageToggle />
            <ThemeToggle />
            <UserMenu user={user} onSignOut={onSignOut} />
          </div>
        </header>

        {/* A language change can fail from either control — the one up here or the
            select on the profile page — so the reason is reported here, next to
            both, rather than only where it happened to be triggered. */}
        {localeError ? (
          <div className="px-4 pt-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-6xl">
              <Banner kind="error">{localeError}</Banner>
            </div>
          </div>
        ) : null}

        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {/*
            Keyed on the path so the entrance animation replays per screen
            rather than only on the first one. Eight pixels and a fade: enough to
            say the content changed, not enough to ask to be watched.
          */}
          <div key={location.pathname} className="animate-fade-up">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
