import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../i18n/useI18n'

/** The zoom steps, in order. Index 0 is the image at its natural size. */
const STEPS = [1, 1.5, 2, 3, 4] as const

/** One image, large, with the controls to get closer.
 *
 * The backdrop is near-black in *both* themes, deliberately: this is a
 * photograph, and the point of a dark surround is to judge the picture against
 * nothing. Following the app's palette here would tint every image, which is the
 * one thing a viewer must not do.
 *
 * Rendered through a portal for the same reason `Modal` is — a `fixed` overlay
 * inside a page that holds a transform gets laid out against the page box rather
 * than the viewport.
 *
 * Zoom is a transform on the image inside a scrolling frame, so at 4× the image
 * pans rather than overflowing the panel and going out of reach. Escape closes,
 * and so does the backdrop; the panel stops propagation so a click on the image
 * does not.
 */
export function ImageViewer({
  src,
  alt,
  onClose,
}: {
  src: string
  alt: string
  onClose(): void
}) {
  const [step, setStep] = useState(0)
  const { t } = useI18n()

  const zoom = STEPS[step]
  const canZoomIn = step < STEPS.length - 1
  const canZoomOut = step > 0

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
      if (event.key === '+' || event.key === '=') setStep((s) => Math.min(s + 1, STEPS.length - 1))
      if (event.key === '-') setStep((s) => Math.max(s - 1, 0))
      if (event.key === '0') setStep(0)
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex animate-fade flex-col bg-black/85 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      {/* The header stops propagation for the same reason the scroll frame below
          does. Without it a click on a zoom control bubbles up to the backdrop's
          onClick, so pressing zoom-in closed the viewer instead of zooming —
          the control and the dismiss handler were firing on the same click. */}
      <header
        className="flex shrink-0 items-center justify-between gap-4 px-4 py-3 text-white/70"
        onClick={(event) => event.stopPropagation()}
      >
        <span className="text-xs tabular-nums">{Math.round(zoom * 100)}%</span>

        <div className="flex items-center gap-1.5">
          <ZoomButton
            label={t('gallery.zoomOut')}
            disabled={!canZoomOut}
            onClick={() => setStep((s) => Math.max(s - 1, 0))}
            glyph="minus"
          />
          <ZoomButton
            label={t('gallery.zoomReset')}
            disabled={step === 0}
            onClick={() => setStep(0)}
            glyph="reset"
          />
          <ZoomButton
            label={t('gallery.zoomIn')}
            disabled={!canZoomIn}
            onClick={() => setStep((s) => Math.min(s + 1, STEPS.length - 1))}
            glyph="plus"
          />
          <button
            type="button"
            onClick={onClose}
            className="ms-2 rounded-control px-2 py-1 text-sm text-white/70 transition-colors duration-150 hover:bg-white/10 hover:text-white"
          >
            {t('generic.close')}
          </button>
        </div>
      </header>

      <div
        className="min-h-0 flex-1 overflow-auto p-4"
        onClick={(event) => event.stopPropagation()}
      >
        <img
          src={src}
          alt={alt}
          className="mx-auto max-w-none transition-transform duration-200 ease-out"
          style={{ transform: `scale(${zoom})` }}
        />
      </div>
    </div>,
    document.body,
  )
}

/** One zoom control, drawn from a name rather than three near-identical blocks. */
function ZoomButton({
  label,
  disabled,
  onClick,
  glyph,
}: {
  label: string
  disabled: boolean
  onClick(): void
  glyph: 'plus' | 'minus' | 'reset'
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="grid h-7 w-7 place-items-center rounded-control text-white/70 transition-colors duration-150 hover:bg-white/10 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent"
    >
      {glyph === 'reset' ? (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="h-4 w-4"
        >
          <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
          <path d="M3 3v5h5" />
        </svg>
      ) : (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          aria-hidden="true"
          className="h-4 w-4"
        >
          {glyph === 'plus' ? (
            <>
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </>
          ) : (
            <path d="M5 12h14" />
          )}
        </svg>
      )}
    </button>
  )
}
