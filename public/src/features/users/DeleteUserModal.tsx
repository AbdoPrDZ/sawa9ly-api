import type { AdminUser } from '../../api/types'
import { Modal } from '../../components/Modal'

/** Confirms a delete, which cascades to keys, clients and orders. */
export function DeleteUserModal({
  user,
  onCancel,
  onConfirm,
}: {
  user: AdminUser
  onCancel(): void
  onConfirm(): void
}) {
  return (
    <Modal title={`Delete ${user.username}?`} onClose={onCancel}>
      <p>
        This removes the user, their API keys, their clients and all their orders. It cannot be
        undone.
      </p>
      <div className="modal-actions">
        <button type="button" className="ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="danger" onClick={onConfirm}>
          Delete user
        </button>
      </div>
    </Modal>
  )
}