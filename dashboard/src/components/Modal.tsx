import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../i18n/useI18n'

/** A dialog. Clicking the backdrop closes it; the panel stops propagation so a
 * click inside does not dismiss it by accident.
 *
 * The backdrop fades and the panel rises, which is enough to say the two are
 * layers. The panel is capped and scrolls rather than growing past the viewport,
 * because the taller forms — the page editor — are well over a screen.
 *
 * Rendered into `document.body` rather than in place, and that is load-bearing
 * rather than tidiness. A page fades up on entry, and a page that is mid- or
 * post-animation can hold a transform; an element with any transform becomes the
 * containing block for `position: fixed` descendants, so a `fixed inset-0`
 * backdrop rendered inside it is laid out against the page box instead of the
 * viewport. The dialog then lands in the wrong place, and — because the panel
 * overflows that smaller box — its buttons end up outside the backdrop and
 * cannot be clicked. A dialog is a top-level surface; the body is where it
 * belongs.
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
  const { t } = useI18n()

  return createPortal(
    <div
      className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/60 p-4 backdrop-blur-[2px] sm:p-6"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="my-auto w-full max-w-md animate-pop-in rounded-panel border border-line bg-surface shadow-pop"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
          <h2>{title}</h2>
          <button
            type="button"
            className="btn btn-ghost -me-1.5 px-1.5 text-lg leading-none"
            onClick={onClose}
            aria-label={t('generic.close')}
          >
            ×
          </button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
