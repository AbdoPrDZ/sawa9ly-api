import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProducts } from '../api/catalogue'
import { listTrackers } from '../api/trackers'
import type { CatalogueProduct } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { EmptyState } from '../components/EmptyState'
import { FetchProduct } from '../components/FetchProduct'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { WatchButton } from '../components/WatchButton'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import type { Translate } from '../i18n/translations'
import { useI18n } from '../i18n/useI18n'

/** The saved catalogue, with a way to fetch a product by its id. */
export function Products() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [watching, setWatching] = useState<Set<number>>(new Set())
  const [notice, setNotice] = useState('')

  const list = usePagedList<CatalogueProduct>(listProducts, { errorKey: 'error.products' })
  const products = list.items

  // The watch state is per user, so it is read once here rather than asked for
  // on every row.
  useEffect(() => {
    listTrackers()
      .then((trackers) =>
        setWatching(new Set(trackers.map((t2) => t2.target?.product_id).filter(isNumber))),
      )
      .catch(() => setWatching(new Set()))
  }, [])

  function onWatched(productId: number, now: boolean) {
    setWatching((current) => {
      const next = new Set(current)
      if (now) next.add(productId)
      else next.delete(productId)
      return next
    })

    setNotice(
      now ? t('products.watching', { id: productId }) : t('products.stopped', { id: productId }),
    )
}

  function onFetched(product: CatalogueProduct) {
    setNotice(t('products.fetched', { id: product.product_id }))
    list.setError('')
    list.reload()
  }

  return (
    <section>
      <PageHeader title={t('products.title')} />

      {/* The one control that reaches the live site, so it is a card of its own
          rather than a row floating above the list. */}
      <div className="card mb-5">
        <FetchProduct onFetched={onFetched} onError={list.setError} />
        <p className="mt-3 text-xs text-muted">{t('products.fetchHint')}</p>
      </div>

{list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.products') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!products ? (
        <MessageSpinner messageKey="loading.products" />
      ) : products.length === 0 ? (
        <EmptyState>
          <p>{list.query.q ? t('products.emptySearch') : t('products.empty')}</p>
          <AdminOnly>
            {/* The command is not translated: it is a thing to be copied, and it
                is the same whatever language the page is in. Only the lead-in
                around it changes. */}
            <p className="mt-2">
              {t('products.emptyCli')}{' '}
              <code>python main.py catalogue save &lt;id&gt; --user &lt;name&gt;</code>
            </p>
          </AdminOnly>
        </EmptyState>
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('products.col.id')}</th>
              <th>{t('products.col.title')}</th>
              <th>{t('products.col.cost')}</th>
              <th>{t('products.col.price')}</th>
              <th>{t('products.col.margin')}</th>
              <th>{t('products.col.available')}</th>
              <th>{t('products.col.images')}</th>
<th>{t('products.col.watch')}</th>
            </tr>
          </thead>
          <tbody>
{products.map((product) => (
              <tr
                key={product.product_id}
                className="cursor-pointer"
                onClick={() => navigate(`/products/${product.product_id}`)}
              >
                <td className="font-mono text-xs text-muted">{product.product_id}</td>
                <td className="max-w-xs truncate font-medium">{product.title ?? t('generic.unknown')}</td>
                <td>{money(product.cost, t)}</td>
                <td>{money(product.price, t)}</td>
                <td>{money(product.margin, t)}</td>
                <td>{product.available ? t('generic.yes') : t('generic.no')}</td>
                <td className="text-muted">{product.images.length}</td>
                <td>
                  <WatchButton
                    productId={product.product_id}
                    watching={watching.has(product.product_id)}
onChanged={(now) => onWatched(product.product_id, now)}
onError={list.setError}
                    size="small"
                  />
                </td>
              </tr>
))}
          </tbody>
        </TablePanel>
      )}

      {products && products.length > 0 && (
        <Pager
          total={list.total}
          page={list.query.page}
          pageSize={PAGE_SIZE}
          hasMore={list.hasMore}
          onPage={list.query.setPage}
        />
      )}
    </section>
  )
}

function isNumber(value: number | undefined): value is number {
  return typeof value === 'number'
}

/** A whole number of dinars, or the shared unknown dash. */
function money(value: number | null, t: Translate) {
  return value === null ? t('generic.unknown') : value.toLocaleString()
}


