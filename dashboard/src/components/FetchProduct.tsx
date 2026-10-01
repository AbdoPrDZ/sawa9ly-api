import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { saveProduct } from '../api/catalogue'
import type { CatalogueProduct } from '../api/types'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'

interface FetchProductProps {
  onFetched(product: CatalogueProduct): void
  onError(message: string): void
  /** Shown when the page already has a list, so it does not offer a second way in. */
  autoFocus?: boolean
}

/** Fetches a product from the site by its sawa9ly id, and stores it.
 *
 * This is the one action in the dashboard that reaches the live site, so it is
 * a deliberate form rather than a button on every row.
 *
 * Drawn as a card by the page that owns it, so the layout here is the row inside
 * that card: label, field, button.
 */
export function FetchProduct({ onFetched, onError, autoFocus = false }: FetchProductProps) {
  const { t } = useI18n()
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const productId = Number(value.trim())

    if (!Number.isInteger(productId) || productId <= 0) {
      onError(t('products.fetchInvalid'))
      return
    }

    setBusy(true)

    try {
      onFetched(await saveProduct(productId))
      setValue('')
    } catch (caught) {
      // A 404 from the site means the id is not a product. That sentence is worth
      // saying properly — it names the id and where to check it — and the server's
      // version of it is English, so it is rebuilt here in the reader's language.
      onError(
        caught instanceof ApiError && caught.status === 404
          ? t('products.notFound', { id: productId })
          : apiErrorMessage(caught, t, 'products.fetchFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <label className="flex-1">
        <span className="mb-1.5 block text-xs font-medium text-muted">
          {t('products.fetchLabel')}
        </span>
        <input
          type="number"
          min={1}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={t('products.fetchPlaceholder')}
          aria-label={t('products.fetchAria')}
          autoFocus={autoFocus}
          required
        />
      </label>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? t('products.fetchBusy') : t('products.fetchSubmit')}
      </button>
    </form>
  )
}
