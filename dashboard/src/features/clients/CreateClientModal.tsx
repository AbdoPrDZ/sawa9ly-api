import { useState } from 'react'
import type { FormEvent } from 'react'
import type { NewClient } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'
import { WilayaCommuneFields } from './WilayaCommuneFields'

/**
 * Adds a delivery recipient, or edits one already stored under the same name.
 *
 * The fields are the site's own checkout form, so the labels match what sawa9ly
 * asks for. Only the name is required; the site validates the rest at checkout
 * time, which is why nothing here is marked required.
 *
 * The field names are translated but not the column headers the site uses, and
 * `adresse` is left as the site's own French spelling rather than corrected —
 * it is the word on their form, and matching it is the point.
 *
 * **No note field.** A note belongs to an order or to one of its lines, and both
 * of those still have one; on a recipient it was never read.
 *
 * The wilaya and the commune are a pair, so they are one component rather than two
 * fields here: the commune list depends on the wilaya, and a form that let you set
 * them independently would happily produce a pair the site rejects.
 */
export function CreateClientModal({
  onCancel,
  onSubmit,
}: {
  onCancel(): void
  onSubmit(input: NewClient): Promise<void>
}) {
  const { t } = useI18n()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [adresse, setAdresse] = useState('')
  const [wilayaId, setWilayaId] = useState('')
  const [communeId, setCommuneId] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    // Blank boxes are sent as null, which the server treats as "leave whatever
    // is already stored alone" when the name matches an existing client. The
    // two id boxes are numbers, so an empty one has to become null rather than
    // NaN, which is what Number('') would give.
    const wilaya = wilayaId.trim() === '' ? null : Number(wilayaId)
    const commune = communeId.trim() === '' ? null : Number(communeId)

    try {
      await onSubmit({
        full_name: fullName.trim(),
        phone: phone.trim() || null,
        adresse: adresse.trim() || null,
        wilaya_id: wilaya,
        commune_id: commune,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('client.modalTitle')} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label={t('client.fieldName')} hint={t('client.fieldNameHint')}>
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            autoComplete="name"
            autoFocus
            required
          />
        </Field>

        <Field label={t('client.fieldPhone')} hint={t('client.fieldPhoneHint')}>
          <input value={phone} onChange={(event) => setPhone(event.target.value)} autoComplete="tel" />
        </Field>

        <Field label={t('client.fieldAdresse')} hint={t('client.fieldAdresseHint')}>
          <input value={adresse} onChange={(event) => setAdresse(event.target.value)} />
        </Field>

        <WilayaCommuneFields
          wilayaId={wilayaId}
          communeId={communeId}
          onChange={(nextWilaya, nextCommune) => {
            setWilayaId(nextWilaya)
            setCommuneId(nextCommune)
          }}
        />

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy || !fullName.trim()}>
            {busy ? t('client.busy') : t('client.submit')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
