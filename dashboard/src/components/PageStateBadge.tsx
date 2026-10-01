import { useI18n } from '../i18n/useI18n'
import type { PageState } from '../api/types'

/** Where a page is in its life, as a badge.
 *
 * Only `publish` reads as live. A draft and an archive are both "not being
 * served", but for opposite reasons, so they are told apart rather than merged
 * into one grey: a draft is still being written, an archive has been retired.
 */
export function PageStateBadge({ state }: { state: PageState }) {
  const { t } = useI18n()

  if (state === 'publish') return <span className="badge badge-ok">{t('pages.state.publish')}</span>
  if (state === 'archive') return <span className="badge badge-danger">{t('pages.state.archive')}</span>
  return <span className="badge">{t('pages.state.draft')}</span>
}
