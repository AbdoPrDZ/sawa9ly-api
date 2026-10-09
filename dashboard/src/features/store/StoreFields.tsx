import { useState } from 'react'
import { Field } from '../../components/Field'
import { useI18n } from '../../i18n/useI18n'

/** The store fields, shared by the profile page and the user modals.
 *
 * The three move together: the two names are what make a store, and the logo is
 * optional. The logo is read in the browser and passed on as the data URI the
 * server stores, which is why the type and size checks live here as well as on
 * the server — a quick answer beats an upload that is refused after the fact.
 */
export interface StoreValue {
  name: string
  slug: string
  logo: string | null
}

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
const MAX_BYTES = 256 * 1024

export function StoreFields({
  value,
  onChange,
}: {
  value: StoreValue
  onChange(next: StoreValue): void
}) {
  const { t } = useI18n()
  const [logoError, setLogoError] = useState('')

  function pickLogo(file: File | undefined) {
    setLogoError('')

    if (!file) return

    if (!ALLOWED_TYPES.includes(file.type)) {
      setLogoError(t('store.errorType'))
      return
    }

    if (file.size > MAX_BYTES) {
      setLogoError(t('store.errorSize'))
      return
    }

    const reader = new FileReader()
    reader.onload = () => onChange({ ...value, logo: String(reader.result) })
    reader.readAsDataURL(file)
  }

  return (
    <>
      <Field label={t('store.fieldName')} hint={t('store.fieldNameHint')}>
        <input
          value={value.name}
          onChange={(event) => onChange({ ...value, name: event.target.value })}
        />
      </Field>

      <Field label={t('store.fieldSlug')} hint={t('store.fieldSlugHint')}>
        <input
          value={value.slug}
          placeholder="my-store"
          onChange={(event) => onChange({ ...value, slug: event.target.value })}
        />
      </Field>

      <Field label={t('store.fieldLogo')} hint={t('store.fieldLogoHint')}>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          onChange={(event) => pickLogo(event.target.files?.[0])}
        />
      </Field>

      {logoError ? <p className="mb-3 text-xs text-danger">{logoError}</p> : null}

      {value.logo ? (
        <div className="mb-3 flex items-center gap-3">
          <img
            src={value.logo}
            alt=""
            className="h-12 w-12 rounded-lg border border-line object-cover"
          />
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onChange({ ...value, logo: null })}
          >
            {t('store.removeLogo')}
          </button>
        </div>
      ) : null}

      {value.slug ? (
        <p className="text-xs text-muted">{t('store.urlPreview', { slug: value.slug })}</p>
      ) : null}
    </>
  )
}
