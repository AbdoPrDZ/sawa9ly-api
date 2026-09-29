import { useState } from 'react'
import type { FormEvent } from 'react'
import type { CatalogueProduct, NewPage } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'

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
    <Modal title="New landing page" onClose={onCancel}>
      <form onSubmit={submit}>
        <Field
          label="Product"
          hint={
            products.length
              ? 'The sawa9ly id is what gets stored. A product not in the list can still be added by typing its id.'
              : 'Nothing saved in the catalogue yet. Type the sawa9ly product id.'
          }
        >
          <input
            list="page-product-ids"
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
            placeholder="5663"
            autoFocus
            required
          />
          <datalist id="page-product-ids">
            {products.map((product) => (
              <option key={product.product_id} value={product.product_id}>
                {product.title ?? 'Untitled product'}
              </option>
            ))}
          </datalist>
        </Field>

        <Field label="Title" hint="What the page is called in this list.">
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </Field>

        <Field
          label="HTML"
          hint="The page markup, stored as written. Nothing renders it yet, so it cannot break this dashboard."
        >
          <textarea
            rows={10}
            value={html}
            onChange={(event) => setHtml(event.target.value)}
            spellCheck={false}
          />
        </Field>

        <div className="modal-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="submit"
            className="primary"
            disabled={busy || !productId.trim() || !title.trim()}
          >
            {busy ? 'Creating…' : 'Create page'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
