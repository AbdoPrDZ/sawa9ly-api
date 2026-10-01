import type { ReactNode } from 'react'

/** What a list shows instead of rows when there are none.
 *
 * A panel rather than a line of grey text, so an empty screen is clearly a state
 * of the page and not a failure to load one.
 */
export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="panel px-6 py-14 text-center text-sm text-muted">{children}</div>
}
