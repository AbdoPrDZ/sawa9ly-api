import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { updateProfile } from '../api/profile'
import type { Locale } from '../api/types'
import { en } from './catalog/en'
import { I18nContext } from './context'
import type { I18n } from './context'
import { directionOf, LOCALES, translatorFor } from './translations'
import { useSession } from '../session/useSession'

/** Where the login screen's language is remembered, so the sign-in form is not
 * stranded in English for somebody who reads French.
 *
 * Deliberately *not* the account's language, and deliberately not sent anywhere:
 * it only decides what the screen looks like before there is a session. The
 * account's own language is on the server and always wins once signed in — so
 * signing in from a new device, or from a shared one, cannot quietly change it.
 */
const REMEMBERED_KEY = 'sawa9ly.dashboard.locale'

function readRemembered(): Locale | null {
  const stored = localStorage.getItem(REMEMBERED_KEY)
  return LOCALES.includes(stored as Locale) ? (stored as Locale) : null
}

/** The language the whole interface is rendered in.
 *
 * **The server decides which language this is**, and the value arrives on the
 * signed-in user rather than being read from the browser. That is not
 * incidental: the same value chooses the language of this user's Telegram
 * notifications, so a language kept only in local storage would let the screen
 * and the notifications disagree — and on another device the screen would be the
 * one that looks wrong.
 *
 * Two things are set on the document from here, and both have to be document
 * level because CSS and the browser need them rather than React:
 *
 * - `lang`, so the browser picks the right font for Arabic, hyphenates
 *   correctly, and gives a screen reader the right pronunciation;
 * - `dir`, which is what mirrors the sidebar, the tables and the modals. The CSS
 *   has to be written in logical properties for this to be enough.
 *
 * The provider sits **above** the signed-in check, because the login screen is
 * translated too and has no user to read a language from.
 *
 * `override` is the optimistic language — the one the reader just asked for,
 * before the server has confirmed it. It exists so a control in the top bar can
 * switch instantly, and it is dropped the moment the account's own value catches
 * up, so the server remains the authority and never something to catch up *to*.
 */
export function I18nProvider({
  accountLocale,
  children,
}: {
  /** The signed-in user's language, or undefined when there is no session. */
  accountLocale?: Locale
  children: ReactNode
}) {
  const { refresh } = useSession()

  const [remembered, setRemembered] = useState<Locale | null>(readRemembered)
  const [override, setOverride] = useState<Locale | null>(null)
  const [savingLocale, setSavingLocale] = useState(false)
  const [localeError, setLocaleError] = useState<string | null>(null)

  const locale = override ?? accountLocale ?? remembered ?? 'en'

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = directionOf(locale)
  }, [locale])

  // The account has spoken; the optimistic value has served its purpose. This is
  // also what stops an override surviving a sign-out and colouring the login
  // screen of the next person.
  useEffect(() => {
    if (accountLocale === undefined) return
    setOverride(null)
  }, [accountLocale])

  // Only remembered while signed out. Once the account has an opinion, the
  // account's value is the one that counts and this must not drift away from it.
  useEffect(() => {
    if (accountLocale || !remembered || remembered === locale) return

    localStorage.setItem(REMEMBERED_KEY, locale)
    setRemembered(locale)
  }, [accountLocale, remembered, locale])

  const setLocale = useCallback(
    (next: Locale) => {
      if (next === locale) return

      // Change the screen first. This is a control the reader just pressed, and
      // a language that arrives 200ms later reads as the click having missed.
      setOverride(next)
      setLocaleError(null)
      localStorage.setItem(REMEMBERED_KEY, next)
      setRemembered(next)

      if (accountLocale === undefined) return

      setSavingLocale(true)

      updateProfile({ locale: next })
        .then(refresh)
        .catch((error: unknown) => {
          // Put the old language back rather than leaving the screen showing one
          // the server refused. The account's value never changed, so dropping
          // the override is the whole revert.
          setOverride(null)
          setLocaleError(
            error instanceof Error ? error.message : 'Could not save the language.',
          )
        })
        .finally(() => setSavingLocale(false))
    },
    [accountLocale, locale, refresh],
  )

  const value = useMemo<I18n>(
    () => ({
      locale,
      direction: directionOf(locale),
      t: translatorFor(locale),
      // Each language named in itself, read from the English catalogue so the
      // three names are written in exactly one place. A picker listing the
      // choices in a language the reader may not know is not a picker.
      languageNames: {
        en: en['profile.language.en'],
        fr: en['profile.language.fr'],
        ar: en['profile.language.ar'],
      },
      locales: LOCALES,
      setLocale,
      savingLocale,
      localeError,
    }),
    [locale, setLocale, savingLocale, localeError],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
