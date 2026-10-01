import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Page, PageEdits, PageState } from '../../api/types'
import { Field } from '../../components/Field'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'
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
  const { t } = useI18n()
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
    <Modal title={t('page.editTitle')} onClose={onCancel}>
      <form onSubmit={submit}>
        {/* The product is fixed once a page exists, so it is stated rather than
            offered as a control: moving a page to another product means writing
            a new one. */}
        <p className="mb-3.5 text-sm text-muted">
          {page.sawa9ly_product_id === null
            ? t('page.editProductGone')
            : t('page.editForProduct', { id: page.sawa9ly_product_id })}
          {page.product_title ? ` — ${page.product_title}` : ''}
        </p>

        <Field
          label={t('page.fieldLink')}
          hint={page.state === 'publish' ? t('page.fieldLinkHintPublished') : t('page.fieldLinkHintDraft')}
        >
          <input readOnly value={publicUrl(page)} onFocus={(event) => event.target.select()} />
        </Field>

        <Field label={t('page.fieldEditTitle')} hint={t('page.fieldEditTitleHint')}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </Field>

        <Field label={t('page.fieldState')} hint={t('page.fieldStateHint')}>
          <select value={state} onChange={(event) => setState(event.target.value as PageState)}>
            <option value="draft">{t('pages.state.draft')}</option>
            <option value="publish">{t('pages.state.publish')}</option>
            <option value="archive">{t('pages.state.archive')}</option>
          </select>
        </Field>

        <Field label={t('page.fieldEditHtml')} hint={t('page.fieldEditHtmlHint')}>
          <textarea
            rows={12}
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
            disabled={busy || (!titleChanged && !htmlChanged && !stateChanged)}
          >
            {busy ? t('generic.saving') : t('generic.save')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
