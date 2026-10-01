import { useState } from 'react'
import { listTrackers, unwatch, watch } from '../api/trackers'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'

interface WatchButtonProps {
  productId: number
  /** Whether the signed-in user is already watching it. */
  watching: boolean
  onChanged(watching: boolean): void
  onError(message: string): void
  size?: 'small' | 'normal'
}

/** Turns watching a product on and off, and reflects the state afterwards.
 *
 * Watching is a subscription the queue acts on, not a fetch: nothing is
 * requested from the site here, so the button is safe to press repeatedly.
 *
 * In a table row it draws as a badge, because a column of buttons is a column of
 * noise and the state itself is the information. On a product's own page, where
 * it is the only control of its kind, it is an ordinary button.
 */
export function WatchButton({
  productId,
  watching,
  onChanged,
  onError,
  size = 'normal',
}: WatchButtonProps) {
  const [busy, setBusy] = useState(false)
  const { t } = useI18n()

  async function toggle() {
    setBusy(true)

    try {
      if (watching) {
        await unwatch(productId)
        onChanged(false)
      } else {
        await watch(productId)
        onChanged(true)
      }
    } catch (caught) {
      onError(apiErrorMessage(caught, t, 'product.watchFailed'))
      // The server is the truth about the current state, so re-read rather than
      // leaving the button showing whatever the failed attempt intended.
      try {
        const trackers = await listTrackers()
        const still = trackers.some((t) => t.target?.product_id === productId)
        onChanged(still)
      } catch {
        onChanged(watching)
      }
    } finally {
      setBusy(false)
    }
  }

  const className =
    size === 'small'
      ? watching
        ? 'badge badge-ok cursor-pointer'
        : 'btn btn-ghost btn-sm'
      : watching
        ? 'btn btn-primary'
        : 'btn'

  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      aria-pressed={watching}
      onClick={toggle}
    >
      {busy ? '…' : watching ? 'Watching' : 'Track'}
    </button>
  )
}
