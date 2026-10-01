import { useContext } from 'react'
import { I18nContext } from './context'

/** The active language, and the `t` that renders into it.
 *
 * Throws outside the provider rather than falling back to English: a component
 * that reaches for this outside the tree is a wiring mistake, and quietly
 * rendering in the wrong language would hide it.
 */
export function useI18n() {
  const i18n = useContext(I18nContext)

  if (!i18n) {
    throw new Error('useI18n must be used inside <I18nProvider>')
  }

  return i18n
}
