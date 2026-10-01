import { useI18n } from '../i18n/useI18n'

/** Why a key does or does not still work. Three states, not two, because
 * "expired" and "revoked" need different reactions.
 *
 * Expired is amber rather than red: the key is broken, but it expired on its own
 * and nothing went wrong. Red is kept for a revoke, which is a deliberate act.
 */
export function KeyState({ revoked, usable }: { revoked: boolean; usable: boolean }) {
  const { t } = useI18n()

  if (revoked) return <span className="badge badge-danger">{t('keys.state.revoked')}</span>
  if (!usable) return <span className="badge badge-warn">{t('keys.state.expired')}</span>
  return <span className="badge badge-ok">{t('keys.state.active')}</span>
}
