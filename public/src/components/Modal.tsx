import type { ReactNode } from 'react'

/** A dialog. Clicking the backdrop closes it; the panel stops propagation so a
 * click inside does not dismiss it by accident.
 */
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose(): void
  children: ReactNode
}) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="modal-head">
          <h2>{title}</h2>
          <button type="button" className="ghost" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        {children}
      </div>
    </div>
  )
}