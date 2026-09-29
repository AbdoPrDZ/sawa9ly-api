import { useState } from 'react'
import type { FormEvent } from 'react'
import type { NewUser, Role } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

/** Creates a user.
 *
 * There is no sawa9ly field, and not by role: no admin sets another user's site
 * credentials at all. They are the user's own to enter, from their profile, and
 * an admin who could type them in could also act as that user on sawa9ly. An
 * administrator's job here is the account and the password to reach it with.
 */
export function CreateUserModal({
  onCancel,
  onSubmit,
}: {
  onCancel(): void
  onSubmit(input: NewUser): Promise<void>
}) {
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<Role>('user')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    try {
      await onSubmit({
        username,
        role,
        password: password || undefined,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Add user" onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label="Username">
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoFocus
          />
        </Field>

        <Field label="Role">
          <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </Field>

        <Field label="Dashboard password" hint="Leave empty to create an API-only user.">
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>

        <p className="muted">
          The new user sets their own sawa9ly email, sawa9ly password and Telegram
          chat from their profile.
        </p>

        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Creating…' : 'Create user'}
          </button>
        </div>
      </form>
    </Modal>
  )
}