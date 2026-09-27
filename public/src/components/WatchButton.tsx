import { useState } from 'react'
import { listTrackers, unwatch, watch } from '../api/trackers'

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
 */
export function WatchButton({
  productId,
  watching,
  onChanged,
  onError,
  size = 'normal',
}: WatchButtonProps) {
  const [busy, setBusy] = useState(false)

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
      onError(caught instanceof Error ? caught.message : 'Could not update the watch.')
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

  const className = watching
    ? size === 'small'
      ? 'badge badge-active toggle'
      : 'primary'
    : size === 'small'
      ? 'ghost toggle'
      : 'ghost'

  return (
    <button type="button" className={className} disabled={busy} onClick={toggle}>
      {busy ? '…' : watching ? 'Watching' : 'Track'}
    </button>
  )
}
