import type { ReactNode } from 'react'

/** A message about the state of the page: an error, a confirmation, a warning. */
export function Banner({
  kind,
  children,
}: {
  kind: 'error' | 'info' | 'success'
  children: ReactNode
}) {
  return <div className={`banner banner-${kind}`}>{children}</div>
}
