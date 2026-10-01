import type { ReactNode } from 'react'

/** The title row every screen opens with, and whatever sits opposite it.
 *
 * Wrapping rather than clipping: on a narrow screen the actions drop below the
 * title instead of squeezing it, which is what a flex-wrap here buys.
 */
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
      <h2>{title}</h2>
      {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
    </div>
  )
}
