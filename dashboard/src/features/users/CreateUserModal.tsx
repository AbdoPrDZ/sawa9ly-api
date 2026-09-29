import { useState } from 'react'
import type { FormEvent } from 'react'
import type { NewUser, Role } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

/** Creates a user.
 *
 * The sawa9ly fields are only rendered for a super: an ordinary administrator
 * adds a user who then sets their own site credentials from their profile. The
 * server refuses those fields for a non-super regardless, so hiding them here is
 * about not offering something that will be rejected.
 */
export function CreateUserModal({
  canSetSiteCredentials,
  onCancel,
  onSubmit,
}: {
  canSetSiteCredentials: boolean
  onCancel(): void
  onSubmit(input: NewUser): Promise<void>
}) {
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<Role>('user')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    try {
      await onSubmit({
        username,
        role,
        password: password || undefined,
        sawa9ly_email: canSetSiteCredentials && email ? email : undefined,
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

        <Field
          label="Sawa9ly email"
          hint={
            canSetSiteCredentials
              ? 'Optional. The user can also set this from their profile.'
              : undefined
          }
        >
          {canSetSiteCredentials ? (
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          ) : (
            <p className="muted">
              The new user sets their own sawa9ly email and password from their profile.
            </p>
          )}
        </Field>

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