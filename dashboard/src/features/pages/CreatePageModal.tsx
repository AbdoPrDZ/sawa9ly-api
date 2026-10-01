import { useState } from 'react'
import type { FormEvent } from 'react'
import type { CatalogueProduct, NewPage } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/**
 * Starts a draft landing page for one product.
 *
 * The product is picked from the saved catalogue, and a product that has never
 * been saved can still be named by its sawa9ly id — the server creates the
 * catalogue row for it, the same way an order line does.
 */
export function CreatePageModal({
  products,
  onCancel,
  onSubmit,
}: {
  products: CatalogueProduct[]
  onCancel(): void
  onSubmit(input: NewPage): Promise<void>
}) {
  const { t } = useI18n()
  const [productId, setProductId] = useState('')
  const [title, setTitle] = useState('')
  const [html, setHtml] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    try {
      await onSubmit({ product_id: Number(productId), title: title.trim(), html })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('page.modalTitle')} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field
          label={t('page.fieldProduct')}
          hint={products.length ? t('page.fieldProductHint') : t('page.fieldProductHintEmpty')}
        >
          <input
            list="page-product-ids"
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
            placeholder="5663"
            autoFocus
            required
          />
          {/* The datalist options are the product's own title, which is the
              site's wording and is not translated. A datalist has no label of
              its own to set, so the association is the `list` attribute above. */}
          <datalist id="page-product-ids">
            {products.map((product) => (
              <option key={product.product_id} value={product.product_id}>
                {product.title ?? 'Untitled product'}
              </option>
            ))}
          </datalist>
        </Field>

        <Field label={t('page.fieldTitle')} hint={t('page.fieldTitleHint')}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </Field>

        <Field label={t('page.fieldHtml')} hint={t('page.fieldHtmlHint')}>
          <textarea
            rows={10}
            value={html}
            onChange={(event) => setHtml(event.target.value)}
            spellCheck={false}
          />
        </Field>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={busy || !productId.trim() || !title.trim()}
          >
            {busy ? t('page.busy') : t('page.submit')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
