import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Page, PageEdits, PageState } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { publicUrl } from './publicUrl'

/**
 * Edits one page: its title, its markup, or which state it is in.
 *
 * Only the fields that were actually changed are sent, because the API treats an
 * absent key as "leave it alone" — which matters here, where the markup is large
 * and an empty box means "clear this", not "I did not touch it".
 */
export function EditPageModal({
  page,
  onCancel,
  onSubmit,
}: {
  page: Page
  onCancel(): void
  onSubmit(edits: PageEdits): Promise<void>
}) {
  const [title, setTitle] = useState(page.title)
  const [html, setHtml] = useState(page.html)
  const [state, setState] = useState<PageState>(page.state)
  const [busy, setBusy] = useState(false)

  const titleChanged = title !== page.title
  const htmlChanged = html !== page.html
  const stateChanged = state !== page.state

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)

    const edits: PageEdits = {}
    if (titleChanged) edits.title = title.trim()
    if (htmlChanged) edits.html = html
    if (stateChanged) edits.state = state

    try {
      await onSubmit(edits)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Edit page" onClose={onCancel}>
      <form onSubmit={submit}>
        {/* The product is fixed once a page exists, so it is stated rather than
            offered as a control: moving a page to another product means writing
            a new one. */}
        <p className="muted">
          {page.sawa9ly_product_id === null
            ? 'This page’s product is no longer in the catalogue.'
            : `For product ${page.sawa9ly_product_id}`}
          {page.product_title ? ` — ${page.product_title}` : ''}
        </p>

        <Field
          label="Public link"
          hint={
            page.state === 'publish'
              ? 'Live at /pages/. Open it in a new tab to see what a visitor sees.'
              : 'Not served yet — only a page in the publish state answers this address.'
          }
        >
          <input readOnly value={publicUrl(page)} onFocus={(event) => event.target.select()} />
        </Field>

        <Field label="Page title" hint="What this page is called in your list.">
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </Field>

        <Field label="State" hint="Only publish is live. Archive keeps the page without serving it.">
          <select value={state} onChange={(event) => setState(event.target.value as PageState)}>
            <option value="draft">draft</option>
            <option value="publish">publish</option>
            <option value="archive">archive</option>
          </select>
        </Field>

        <Field
          label="HTML"
          hint="The page markup. Clearing this box empties the page — that is a real change, not a skipped one."
        >
          <textarea
            rows={12}
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
            disabled={busy || (!titleChanged && !htmlChanged && !stateChanged)}
          >
            {busy ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
