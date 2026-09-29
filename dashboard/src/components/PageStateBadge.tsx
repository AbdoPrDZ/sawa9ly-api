import type { PageState } from '../api/types'

/** Where a page is in its life, as a badge.
 *
 * Only `publish` reads as live. A draft and an archive are both "not being
 * served", but for opposite reasons, so they are told apart rather than merged
 * into one grey.
 */
export function PageStateBadge({ state }: { state: PageState }) {
  if (state === 'publish') return <span className="badge badge-active">publish</span>
  if (state === 'archive') return <span className="badge badge-expired">archive</span>
  return <span className="badge">draft</span>
}
