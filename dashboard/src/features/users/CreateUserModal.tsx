import { useState } from 'react'
import type { FormEvent } from 'react'
import type { NewUser, Role } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

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
  const { t } = useI18n()
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
    <Modal title={t('user.modalTitle')} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label={t('user.fieldUsername')}>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoFocus
          />
        </Field>

        <Field label={t('user.fieldRole')}>
          {/* The options are the two roles this form can assign, spelled in the
              reader's language — a select has no way to say "same as the
              account I just created". `super` is not offered: the API refuses it,
              and a dropdown that 403s is worse than one that is not there. */}
          <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
            <option value="user">{t('role.user')}</option>
            <option value="admin">{t('role.admin')}</option>
          </select>
        </Field>

        <Field label={t('user.fieldPassword')} hint={t('user.fieldPasswordHint')}>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>

        <p className="text-sm text-muted">{t('user.newUserNote')}</p>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? t('user.busy') : t('user.submit')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
