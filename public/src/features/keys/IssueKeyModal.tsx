import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AdminUser } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

/** Issues a key for a user. Label and expiry are optional. */
export function IssueKeyModal({
  users,
  onCancel,
  onSubmit,
}: {
  users: AdminUser[]
  onCancel(): void
  onSubmit(input: { userId: number; label: string; days?: number }): Promise<void>
}) {
  const [userId, setUserId] = useState(users[0]?.id ?? 0)
  const [label, setLabel] = useState('')
  const [expires, setExpires] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    const days = Number(expires)

    try {
      await onSubmit({
        userId,
        label,
        // A zero or blank box means "no expiry" rather than expiring today.
        days: expires && days > 0 ? days : undefined,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Issue an API key" onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label="User">
          <select value={userId} onChange={(event) => setUserId(Number(event.target.value))}>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.username} ({user.role})
              </option>
            ))}
          </select>
        </Field>

        <Field label="Label" hint="Optional. Helps you remember what the key is for.">
          <input value={label} onChange={(event) => setLabel(event.target.value)} />
        </Field>

        <Field label="Expires in days" hint="Leave empty for a key that never expires.">
          <input
            type="number"
            min={1}
            value={expires}
            onChange={(event) => setExpires(event.target.value)}
          />
        </Field>

        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Issuing…' : 'Issue key'}
          </button>
        </div>
      </form>
    </Modal>
  )
}