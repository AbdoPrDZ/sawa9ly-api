import type { Locale } from '../api/types'
import { ar as AR } from './catalog/ar'
import { en as EN } from './catalog/en'
import type { MessageKey } from './catalog/en'
import { fr as FR } from './catalog/fr'

/** What one rendered string costs: the key, and the values for its `{fields}`.
 *
 * A typed signature rather than a plain map lookup, so a key that takes no
 * fields does not need `t('key')` and a key that does cannot be called without
 * them: `t('loading.order')` where the template wants `{id}` is a type error
 * instead of a literal `{id}` in the middle of a sentence.
 */
export type Translate = <K extends MessageKey>(
  key: K,
  fields?: Record<string, string | number>,
) => string

export const LOCALES: Locale[] = ['en', 'fr', 'ar']

/** Written right to left. The document's `dir` is set from this, and it is the
 * only reason the dashboard's CSS has to use logical properties.
 */
const RTL_LOCALES: Locale[] = ['ar']

export const CATALOGUES: Record<Locale, Record<MessageKey, string>> = {
  en: EN,
  fr: FR,
  ar: AR,
}

/** Whether this language runs right to left. */
export function directionOf(locale: Locale): 'ltr' | 'rtl' {
  return RTL_LOCALES.includes(locale) ? 'rtl' : 'ltr'
}

/** Build a `t` for one language.
 *
 * **A key missing from the chosen language falls back to English rather than
 * throwing.** A dashboard that renders one button in the wrong language is a
 * rough edge; one that throws mid-render is a blank page. The catalogues are
 * typed as complete `MessageKey` maps, so forgetting a translation cannot even
 * compile — this is the floor, not the plan.
 *
 * A field the caller supplied that the template does not use *is* a bug, and
 * throws with the key named: it almost always means the key was renamed in `en`
 * and the copy that passes it was not updated, which would otherwise show up as
 * a sentence with a hole in it.
 */
export function translatorFor(locale: Locale): Translate {
  const catalogue = CATALOGUES[locale] ?? CATALOGUES.en

  return (key, fields) => {
    const template = catalogue[key] ?? CATALOGUES.en[key]

    if (template === undefined) {
      console.error(`[i18n] no message named "${key}" in any language`)
      return key
    }

    if (!fields) return template

    for (const name of Object.keys(fields)) {
      if (!template.includes(`{${name}}`)) {
        throw new Error(`[i18n] "${key}" was given a field "{${name}}" it does not use`)
      }
    }

    return template.replace(/\{(\w+)\}/g, (whole, name) =>
      name in fields ? String(fields[name]) : whole,
    )
  }
}
