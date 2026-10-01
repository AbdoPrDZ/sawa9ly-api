import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AdminUser, KeyType } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/** The two surfaces a key can be accepted by, in the order the picker offers
 * them. `api` first because it is the commoner of the two: most keys here exist
 * for a script.
 */
const KEY_TYPES: KeyType[] = ['api', 'mcp']

/** What the form collects.
 *
 * `userId` is null when there was nobody to choose, which is the case for every
 * account except a `super`: the key is then for the person filling the form in.
 * The page decides which route that means, because issuing for yourself and
 * issuing for another user are two different endpoints, not one with a
 * different argument.
 */
export interface IssueKeyInput {
  userId: number | null
  type: KeyType
  label: string
  days?: number
}

/** Issues a key. Type, label and expiry are optional apart from the type.
 *
 * The user picker is drawn only when `users` is non-empty. A `super` gets it and
 * can issue for anybody; everybody else is issued for themselves, and offering
 * them a list of other accounts would only produce a 403.
 */
export function IssueKeyModal({
  users,
  onCancel,
  onSubmit,
}: {
  users: AdminUser[]
  onCancel(): void
  onSubmit(input: IssueKeyInput): Promise<void>
}) {
  const { t } = useI18n()
  const [userId, setUserId] = useState(users[0]?.id ?? 0)
  const [type, setType] = useState<KeyType>('api')
  const [label, setLabel] = useState('')
  const [expires, setExpires] = useState('')
  const [busy, setBusy] = useState(false)

  const picking = users.length > 0

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    const days = Number(expires)

    try {
      await onSubmit({
        userId: picking ? userId : null,
        type,
        label,
        // A zero or blank box means "no expiry" rather than expiring today.
        days: expires && days > 0 ? days : undefined,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={picking ? t('key.issueTitle') : t('key.issueSelfTitle')} onClose={onCancel}>
      <form onSubmit={submit}>
        {picking ? (
          <Field label={t('key.fieldUser')}>
            <select value={userId} onChange={(event) => setUserId(Number(event.target.value))}>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {/* The username is not a word to translate, but the role beside
                      it is — and it is the reason an operator is looking at this
                      picker at all. */}
                  {user.username} ({user.role === 'super' ? t('role.super') : t(`role.${user.role}`)})
                </option>
              ))}
            </select>
          </Field>
        ) : null}

        <Field label={t('key.fieldType')} hint={t('key.fieldTypeHint')}>
          <select value={type} onChange={(event) => setType(event.target.value as KeyType)}>
            {KEY_TYPES.map((option) => (
              <option key={option} value={option}>
                {t(`key.type.${option}`)}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t('key.fieldLabel')} hint={t('key.fieldLabelHint')}>
          <input value={label} onChange={(event) => setLabel(event.target.value)} />
        </Field>

        <Field label={t('key.fieldExpires')} hint={t('key.fieldExpiresHint')}>
          <input
            type="number"
            min={1}
            value={expires}
            onChange={(event) => setExpires(event.target.value)}
          />
        </Field>

        <p className="text-sm text-muted">{t('key.plaintextHint')}</p>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? t('generic.issuing') : t('generic.issue')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
