import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AdminUser, Role, UserEdits } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

/** Edits a user.
 *
 * Only changed fields are sent, because the API treats an absent key as
 * "unchanged". An empty password box therefore means "leave the password
 * alone" — clearing one has to be deliberate, so it is a CLI action instead.
 */
export function EditUserModal({
  user,
  isSelf,
  onCancel,
  onSubmit,
}: {
  user: AdminUser
  isSelf: boolean
  onCancel(): void
  onSubmit(edits: UserEdits): Promise<void>
}) {
  // Only `user` and `admin` are ever offered, so the state cannot hold the root
  // role. A user that has it returns early below, before the form is rendered.
  const [role, setRole] = useState<Role>(user.role === 'admin' ? 'admin' : 'user')
  const [email, setEmail] = useState(user.sawa9ly_email ?? '')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  // Nothing below the role select is offered for a super: the API refuses it,
  // so the form does not pretend otherwise.
  if (!user.can_be_managed) {
    return (
      <Modal title={`Edit ${user.username}`} onClose={onCancel}>
        <p className="muted">
          {user.username} is a <strong>{user.role}</strong> account. Super accounts are managed
          from the environment or the CLI, not from the dashboard.
        </p>
        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Close
          </button>
        </div>
      </Modal>
    )
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    const edits: UserEdits = { sawa9ly_email: email }
    if (role !== user.role) edits.role = role
    if (password) edits.password = password

    try {
      await onSubmit(edits)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={`Edit ${user.username}`} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label="Role" hint={isSelf ? 'You cannot change your own role.' : undefined}>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
            disabled={isSelf}
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </Field>

        <Field label="Sawa9ly email">
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </Field>

        <Field label="New dashboard password" hint="Leave empty to keep the current one.">
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>

        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}