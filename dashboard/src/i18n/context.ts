import { createContext } from 'react'
import type { Locale } from '../api/types'
import type { Translate } from './translations'

export interface I18n {
  locale: Locale
  direction: 'ltr' | 'rtl'
  t: Translate
  /** Each language named in itself. A picker listing the choices in a language
   *  the reader may not know is not a picker. */
  languageNames: Record<Locale, string>
  /** The languages to offer, in cycle order. */
  locales: Locale[]

  /**
   * Change the language, and remember it on the account.
   *
   * One operation, because the language lives on the account and a control that
   * only changed it on screen would leave the two disagreeing — and the
   * notifications, which follow the account, would keep arriving in the old one.
   *
   * The screen changes **immediately** and the save follows, because this is
   * reachable from a one-click control in the top bar and waiting for a round trip
   * makes a quick switch feel broken. A rejected save puts the old language back
   * and leaves the reason in `localeError`; it does not leave the screen claiming
   * a language the server did not accept.
   */
  setLocale(next: Locale): void

  /** True while a language change is in flight, so a control can hold still. */
  savingLocale: boolean

  /** Why the last language change did not stick, or null. */
  localeError: string | null
}

export const I18nContext = createContext<I18n | null>(null)
