import { useState } from 'react'
import type { FormEvent } from 'react'
import type { CatalogueProduct } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/** Edits a product's sell price.
 *
 * The cost is the site's own price and is shown read-only: it comes from the
 * scrape and is never typed in here. Only `price` is sent, and the server
 * refuses anything else.
 */
export function EditProductPriceModal({
  product,
  onCancel,
  onSubmit,
}: {
  product: CatalogueProduct
  onCancel(): void
  onSubmit(price: number): Promise<void>
}) {
  const { t } = useI18n()
  const [value, setValue] = useState(product.price === null ? '' : String(product.price))
  const [busy, setBusy] = useState(false)

  const parsed = Number(value)
  const valid = Number.isInteger(parsed) && parsed >= 1

  // The margin the entered price would give, so the number that matters is
  // visible while typing rather than after saving.
  const margin = valid && product.cost !== null ? parsed - product.cost : null

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    try {
      await onSubmit(parsed)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('product.priceTitle', { id: product.product_id })} onClose={onCancel}>
      <form onSubmit={submit}>
        <Field label={t('product.fieldCost')} hint={t('product.fieldCostHint')}>
          <input
            type="text"
            value={product.cost === null ? t('generic.unknown') : product.cost.toLocaleString()}
            readOnly
            disabled
          />
        </Field>

        <Field label={t('product.fieldPrice')}>
          <input
            type="number"
            min={1}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            autoFocus
            required
          />
        </Field>

        <p className="mb-4 text-xs text-muted">
          {t('product.fieldMargin')}:{' '}
          {margin === null ? t('generic.unknown') : margin.toLocaleString()}
        </p>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            {t('generic.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy || !valid}>
            {busy ? t('generic.saving') : t('generic.save')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
