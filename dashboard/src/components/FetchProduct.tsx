import { useState } from 'react'
import type { FormEvent } from 'react'
import { saveProduct } from '../api/catalogue'
import type { CatalogueProduct } from '../api/types'

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
 */
export function FetchProduct({ onFetched, onError, autoFocus = false }: FetchProductProps) {
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const productId = Number(value.trim())

    if (!Number.isInteger(productId) || productId <= 0) {
      onError('Enter the numeric product id, e.g. 5663.')
      return
    }

    setBusy(true)

    try {
      onFetched(await saveProduct(productId))
      setValue('')
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : 'Could not fetch the product.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="fetch-form" onSubmit={submit}>
      <input
        type="number"
        min={1}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Product id, e.g. 5663"
        aria-label="Product id to fetch"
        autoFocus={autoFocus}
        required
      />
      <button type="submit" className="primary" disabled={busy}>
        {busy ? 'Fetching…' : 'Fetch from site'}
      </button>
    </form>
  )
}
