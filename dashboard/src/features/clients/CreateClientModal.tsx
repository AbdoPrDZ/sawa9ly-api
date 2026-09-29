import { useState } from 'react'
import type { FormEvent } from 'react'
import type { NewClient } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

/**
 * Adds a delivery recipient, or edits one already stored under the same name.
 *
 * The fields are the site's own checkout form, so the labels match what sawa9ly
 * asks for. Only the name is required; the site validates the rest at checkout
 * time, which is why nothing here is marked required.
 */
export function CreateClientModal({
  onCancel,
  onSubmit,
}: {
  onCancel(): void
  onSubmit(input: NewClient): Promise<void>
}) {
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [adresse, setAdresse] = useState('')
  const [wilayaId, setWilayaId] = useState('')
  const [communeId, setCommuneId] = useState('')
  const [note, setNote] = useState('')
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
        note: note.trim() || null,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Add a delivery recipient" onClose={onCancel}>
      <form onSubmit={submit}>
        <Field
          label="Full name"
          hint="The key. Saving this name again updates that recipient instead of adding a second one."
        >
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            autoComplete="name"
            autoFocus
            required
          />
        </Field>

        <Field label="Phone" hint="The number the site calls to confirm the delivery.">
          <input
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            autoComplete="tel"
          />
        </Field>

        <Field label="Adresse" hint="Street address, as the site wants it written.">
          <input value={adresse} onChange={(event) => setAdresse(event.target.value)} />
        </Field>

        <Field
          label="Wilaya id"
          hint="The site's numeric id for the province, not its name. Needed to reach dispatch."
        >
          <input
            type="number"
            value={wilayaId}
            onChange={(event) => setWilayaId(event.target.value)}
          />
        </Field>

        <Field label="Commune id" hint="The site's numeric id for the commune.">
          <input
            type="number"
            value={communeId}
            onChange={(event) => setCommuneId(event.target.value)}
          />
        </Field>

        <Field label="Note" hint="Optional. Anything worth remembering about them.">
          <input value={note} onChange={(event) => setNote(event.target.value)} />
        </Field>

        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy || !fullName.trim()}>
            {busy ? 'Saving…' : 'Save recipient'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
