import { useState } from 'react'
import { useI18n } from '../i18n/useI18n'
import { apply, DEFAULT_THEME } from '../theme'
import type { Theme } from '../theme'

/** Flips the dashboard between its dark and light palettes.
 *
 * One button rather than a menu: there are two themes, and a control for a
 * binary choice should be a switch you can hit, not a list you have to read. The
 * icon names the theme you would *get*, not the one you are in, so it is never
 * ambiguous which way it goes — and the label names it in the reader's own
 * language, because "switch to light theme" is no help to somebody reading
 * Arabic.
 *
 * The initial value is read from the document rather than from storage, because
 * the inline script in `index.html` has already put it there — reading storage
 * again could disagree with what is on screen if the two were ever out of step.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(
    () => (document.documentElement.dataset.theme as Theme) ?? DEFAULT_THEME,
  )
  const { t } = useI18n()

  function toggle() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    apply(next)
    setTheme(next)
  }

  const goesTo = theme === 'dark' ? t('profile.languageLight') : t('profile.languageDark')
  const label = t('menu.open', { language: goesTo })

  return (
    <button type="button" onClick={toggle} className="btn btn-ghost px-2" aria-label={label} title={label}>
      {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
    </button>
  )
}

/** Shown while dark: the theme this button moves to. */
function SunIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-[1.125rem] w-[1.125rem]"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  )
}

/** Shown while light: the theme this button moves to. */
function MoonIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-[1.125rem] w-[1.125rem]"
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  )
}
