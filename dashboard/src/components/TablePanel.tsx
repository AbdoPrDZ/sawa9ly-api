import type { ReactNode } from 'react'

/** A list of records, drawn on the one surface.
 *
 * The panel owns the border and the rounding and the table is borderless inside
 * it, so the list reads as a single block instead of a stack of ruled rows. The
 * wrapper scrolls sideways, which is what keeps a seven-column table usable on a
 * phone without the layout having to reflow into cards.
 */
export function TablePanel({ children }: { children: ReactNode }) {
  return (
    <div className="panel panel-scroll">
      <table className="data-table">{children}</table>
    </div>
  )
}
