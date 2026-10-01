import { useI18n } from '../i18n/useI18n'
import type { MessageKey } from '../i18n/catalog/en'

/** How each role is coloured.
 *
 * Named per role rather than assembled from the role's name, so a role the
 * server adds later reads as neutral instead of rendering an unstyled class.
 */
const TONES: Record<string, string> = {
  super: 'badge badge-warn',
  admin: 'badge badge-accent',
  user: 'badge',
}

/** The three roles, styled apart so a root account is obvious in a list.
 *
 * The name is translated, because it is a word a person reads rather than a value
 * something matches on: an Arabic reader should not have to recognise the English
 * word "super" to know an account is the root one. The colour, which is what
 * actually carries the warning, is language-independent.
 */
export function RoleBadge({ role }: { role: string }) {
  const { t } = useI18n()

  const key = `role.${role}` as MessageKey

  return <span className={TONES[role] ?? 'badge'}>{t(key)}</span>
}
