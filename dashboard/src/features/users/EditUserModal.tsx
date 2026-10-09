import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AdminUser, Role, UserEdits } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { StoreFields } from '../store/StoreFields'
import type { StoreValue } from '../store/StoreFields'
import { useI18n } from '../../i18n/useI18n'

/** Edits a user.
 *
 * Only changed fields are sent, because the API treats an absent key as
 * "unchanged". An empty password box therefore means "leave the password
 * alone" — clearing one has to be deliberate, so it is a CLI action instead.
 *
 * There is no sawa9ly field, and that is the point: a user owns their site
 * credentials and sets them on their own profile. An admin who could type them
 * in could also act as that user on sawa9ly.
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
  const { t } = useI18n()

  // Only `user` and `admin` are ever offered, so the state cannot hold the root
  // role. A user that has it returns early below, before the form is rendered.
  const [role, setRole] = useState<Role>(user.role === 'admin' ? 'admin' : 'user')
  const [password, setPassword] = useState('')
  const [store, setStore] = useState<StoreValue>({
    name: user.store_name ?? '',
    slug: user.store_slug ?? '',
    logo: user.store_logo,
  })
  const [busy, setBusy] = useState(false)

  // Nothing below the role select is offered for a super: the API refuses it,
  // so the form does not pretend otherwise.
  if (!user.can_be_managed) {
    return (
      <Modal title={t('user.editTitle', { name: user.username })} onClose={onCancel}>
        <p className="text-sm text-muted">
          {t('user.editSuperBody', { name: user.username, role: user.role })}
        </p>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.close')}
          </button>
        </div>
      </Modal>
    )
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    const edits: UserEdits = {}
    if (role !== user.role) edits.role = role
    if (password) edits.password = password
    if (store.name !== (user.store_name ?? '')) edits.store_name = store.name
    if (store.slug !== (user.store_slug ?? '')) edits.store_slug = store.slug
    if (store.logo !== user.store_logo) edits.store_logo = store.logo ?? ''

    try {
      await onSubmit(edits)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('user.editTitle', { name: user.username })} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label={t('user.fieldRole')} hint={isSelf ? t('user.fieldRoleSelf') : undefined}>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
            disabled={isSelf}
          >
            <option value="user">{t('role.user')}</option>
            <option value="admin">{t('role.admin')}</option>
          </select>
        </Field>

        <Field
          label={t('user.fieldNewPassword')}
          hint={isSelf ? t('user.fieldNewPasswordSelf') : t('user.fieldNewPasswordOther')}
        >
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>

        <h4 className="mb-2 mt-4">{t('store.title')}</h4>
        <p className="mb-3 text-xs text-muted">{t('store.optional')}</p>
        <StoreFields value={store} onChange={setStore} />

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? t('generic.saving') : t('generic.save')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
