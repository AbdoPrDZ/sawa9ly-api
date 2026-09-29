import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProducts } from '../api/catalogue'
import { isUnauthorized } from '../api/client'
import { createPage, listPages, updatePage } from '../api/pages'
import type { CatalogueProduct, NewPage, Page, PageEdits } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { PageStateBadge } from '../components/PageStateBadge'
import { Spinner } from '../components/Spinner'
import { CreatePageModal } from '../features/pages/CreatePageModal'
import { EditPageModal } from '../features/pages/EditPageModal'
import { publicUrl } from '../features/pages/publicUrl'
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
  const [pages, setPages] = useState<Page[] | null>(null)
  const [products, setProducts] = useState<CatalogueProduct[]>([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Page | null>(null)

  const load = useCallback(async () => {
    try {
      setPages(await listPages())
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(message(caught, 'Could not load your pages.'))
    }
  }, [invalidate])

  useEffect(() => {
    void load()

    // The catalogue only populates the product picker. A failure there is not
    // worth a message of its own: the id can still be typed by hand.
    listProducts()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [load])

  async function onCreate(input: NewPage) {
    try {
      const created = await createPage(input)
      setCreating(false)
      setError('')
      setNotice(`Created "${created.title}".`)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not create the page.'))
    }
  }

  async function onEdit(edits: PageEdits) {
    if (!editing) return

    try {
      await updatePage(editing.id, edits)
      setEditing(null)
      setError('')
      setNotice('Saved.')
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not save the page.'))
    }
  }

  return (
    <section>
      <div className="section-head">
        <h2>Landing pages</h2>
        <div className="section-actions">
          <button type="button" className="primary" onClick={() => setCreating(true)}>
            New page
          </button>
        </div>
      </div>

      <p className="muted">
        Your own pages, one per product or as many as you like for the same one.
        Nothing serves a page yet — this is where the writing is kept until it is.
      </p>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!pages ? (
        <Spinner label="Loading pages" />
      ) : pages.length === 0 ? (
        <>
          <p className="muted">None yet. Create one above.</p>
          <AdminOnly>
            <p className="muted">
              Or from the command line:{' '}
              <code>python main.py page create 5663 &quot;Summer offer&quot; --user &lt;name&gt;</code>.
            </p>
          </AdminOnly>
        </>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Product</th>
              <th>State</th>
              <th>Public link</th>
              <th>HTML</th>
              <th>Updated</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pages.map((page) => (
              <tr key={page.id}>
                <td>{page.title}</td>
                <td>
                  {page.sawa9ly_product_id === null ? (
                    <span className="muted">removed from catalogue</span>
                  ) : (
                    <Link className="link" to={`/products/${page.sawa9ly_product_id}`}>
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
                    <a
                      className="link"
                      href={publicUrl(page)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      /pages/{page.public_id.slice(0, 8)}…
                    </a>
                  ) : (
                    <span className="muted" title="Only a published page is served">
                      /pages/{page.public_id.slice(0, 8)}…
                    </span>
                  )}
                </td>
                <td className="muted">{page.html.length} chars</td>
                <td className="muted">{page.updated_at ?? '—'}</td>
                <td className="row-actions">
                  <button type="button" onClick={() => setEditing(page)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
