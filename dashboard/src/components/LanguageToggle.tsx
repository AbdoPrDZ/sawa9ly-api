import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../i18n/useI18n'

/** Chooses the dashboard's language, from a menu rather than a cycle.
 *
 * A cycle of three is one click but it is a *guess*: the reader has to work out
 * which press gives the language they want, and the control never says what the
 * options are. A menu costs a second click and always names every option, which
 * is the better trade for something as consequential as the language of a whole
 * interface — and the same reasoning that puts a menu on the avatar rather than
 * two cycles of role and sign-out.
 *
 * The trigger shows the language **you are in**, so the control answers "where am
 * I" without being opened, and each option is named in its own language, so a
 * reader who cannot read the current one can still find theirs.
 *
 * Closes on Escape, on a click outside, and after a choice — the three ways a menu
 * is expected to. Held still while the save is in flight so a second choice cannot
 * race the first and leave the account on a language nobody asked for.
 */
export function LanguageToggle() {
  const { locale, locales, setLocale, languageNames, savingLocale } = useI18n()

  const [open, setOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)

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
        onClick={() => setOpen(!open)}
        disabled={savingLocale}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={languageNames[locale]}
        title={languageNames[locale]}
        className="flex items-center gap-1.5 rounded-full py-1 ps-1.5 pe-2 text-sm transition-colors duration-150 hover:bg-raised"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="h-[1.125rem] w-[1.125rem] flex-none text-muted"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18" />
          <path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18" />
        </svg>
        {/* The name of the current language, in that language. Hidden on the
            narrowest screens, where the globe alone carries it and the menu is
            still one tap away. */}
        <span className="hidden max-w-24 truncate font-medium sm:block">
          {languageNames[locale]}
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
            'h-3.5 w-3.5 flex-none text-faint transition-transform duration-150',
            open ? 'rotate-180' : '',
          ].join(' ')}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open ? (
        <div className="menu mt-2 animate-pop-in" role="menu">
          {locales.map((option) => (
            <button
              key={option}
              type="button"
              role="menuitemradio"
              aria-checked={option === locale}
              onClick={() => {
                setLocale(option)
                setOpen(false)
              }}
              className={[
                'menu-item justify-between',
                // The current one is marked, not just implied by where the tick
                // is: a reader who opened the menu to confirm is served by the
                // same affordance whichever language they are in.
                option === locale ? 'text-ink' : '',
              ].join(' ')}
            >
              <span>{languageNames[option]}</span>
              {option === locale ? (
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                  className="h-4 w-4 flex-none text-accent"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
