import type { AdminApiKey } from '../../api/types'
import { Modal } from '../../components/Modal'

/** Confirms a revoke, which takes effect on the key's next use. */
export function RevokeKeyModal({
  apiKey,
  onCancel,
  onConfirm,
}: {
  apiKey: AdminApiKey
  onCancel(): void
  onConfirm(): void
}) {
  return (
    <Modal title={`Revoke ${apiKey.prefix}…?`} onClose={onCancel}>
      <p>
        Any client using this key stops working immediately. The record stays so you can see the
        key existed.
      </p>
      <div className="modal-actions">
        <button type="button" className="ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="danger" onClick={onConfirm}>
          Revoke key
        </button>
      </div>
    </Modal>
  )
}