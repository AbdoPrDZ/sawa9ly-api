import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProducts } from '../api/catalogue'
import { createPage, listPages, updatePage } from '../api/pages'
import type { CatalogueProduct, NewPage, Page, PageEdits } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { PageStateBadge } from '../components/PageStateBadge'
import { Pager } from '../components/Pager'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { CreatePageModal } from '../features/pages/CreatePageModal'
import { EditPageModal } from '../features/pages/EditPageModal'
import { publicUrl } from '../features/pages/publicUrl'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** The signed-in user's landing pages.
 *
 * A page is one user's writing about one product, so this is self-service like
 * the profile page: every user gets it, and each sees only their own. One user
 * may keep several pages for the same product, so the list is per page rather
 * than per product.
 *
 * The markup is stored, never rendered here. Nothing serves a page yet, so the
 * HTML cannot affect this dashboard.
 */
export function Pages() {
  const { invalidate } = useSession()
  const { t } = useI18n()
const [products, setProducts] = useState<CatalogueProduct[]>([])
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Page | null>(null)

  const list = usePagedList<Page>(listPages, {
    errorKey: 'error.pages',
    onUnauthorized: invalidate,
  })
  const pages = list.items

  useEffect(() => {
    // The catalogue only populates the product picker, so it is asked for the
    // largest page the server will serve rather than a page of the list the
    // picker can scroll through. A failure here is not worth a message of its
    // own: the id can still be typed by hand.
    listProducts({ limit: 200 })
      .then((result) => setProducts(result.items))
      .catch(() => setProducts([]))
  }, [])

  async function onCreate(input: NewPage) {
    try {
const created = await createPage(input)
      setCreating(false)
      list.setError('')
      setNotice(t('pages.created', { title: created.title }))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.pages'))
    }
  }

  async function onEdit(edits: PageEdits) {
    if (!editing) return

    try {
      await updatePage(editing.id, edits)
      setEditing(null)
      list.setError('')
      setNotice(t('pages.saved'))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.pages'))
    }
  }

  return (
    <section>
      <PageHeader title={t('pages.title')}>
        <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
          {t('pages.new')}
        </button>
      </PageHeader>

      <p className="mb-5 max-w-prose text-sm text-muted">{t('pages.intro')}</p>

{list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.pages') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!pages ? (
        <MessageSpinner messageKey="loading.pages" />
      ) : pages.length === 0 ? (
        <EmptyState>
          <p>{list.query.q ? t('pages.emptySearch') : t('pages.empty')}</p>
          <AdminOnly>
            <p className="mt-2">
              {t('pages.emptyCli')}{' '}
              <code>python main.py page create 5663 &quot;Summer offer&quot; --user &lt;name&gt;</code>
            </p>
          </AdminOnly>
        </EmptyState>
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('pages.col.title')}</th>
              <th>{t('pages.col.product')}</th>
              <th>{t('pages.col.state')}</th>
              <th>{t('pages.col.link')}</th>
              <th>{t('pages.col.html')}</th>
              <th>{t('pages.col.updated')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pages.map((page) => (
              <tr key={page.id}>
                <td className="max-w-xs truncate font-medium">{page.title}</td>
                <td>
                  {page.sawa9ly_product_id === null ? (
                    <span className="text-muted">{t('pages.removedFromCatalogue')}</span>
                  ) : (
                    <Link className="btn-link" to={`/products/${page.sawa9ly_product_id}`}>
                      {page.sawa9ly_product_id}
                    </Link>
                  )}
                </td>
                <td>
                  <PageStateBadge state={page.state} />
                </td>
                <td>
                  {/*
                    Only a published page has a working address, so a draft or an
                    archive shows the token without a link rather than a link that
                    404s. The token is shown in both cases: it is how a page is
                    found, and it does not change with the state.
                  */}
                  {page.state === 'publish' ? (
                    <a className="btn-link" href={publicUrl(page)} target="_blank" rel="noreferrer">
                      /pages/{page.public_id.slice(0, 8)}…
                    </a>
                  ) : (
                    <span className="text-muted" title={t('pages.notServed')}>
                      /pages/{page.public_id.slice(0, 8)}…
                    </span>
                  )}
                </td>
                <td className="text-muted">{page.html.length}</td>
                <td className="text-muted">{page.updated_at ?? t('generic.unknown')}</td>
                <td className="text-end">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => setEditing(page)}
                  >
                    {t('generic.edit')}
                  </button>
                </td>
              </tr>
            ))}
</tbody>
        </TablePanel>
      )}

      {pages && pages.length > 0 && (
        <Pager
          total={list.total}
          page={list.query.page}
          pageSize={PAGE_SIZE}
          hasMore={list.hasMore}
          onPage={list.query.setPage}
        />
      )}

      {creating ? (
        <CreatePageModal
          products={products}
          onCancel={() => setCreating(false)}
          onSubmit={onCreate}
        />
      ) : null}

      {editing ? (
        <EditPageModal page={editing} onCancel={() => setEditing(null)} onSubmit={onEdit} />
      ) : null}
    </section>
  )
}

