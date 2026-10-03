import { useState } from 'react'
import { listPrices, syncPrices } from '../api/shipping'
import type { DeliveryPrice, ListQuery } from '../api/types'
import { Banner } from '../components/Banner'
import { EmptyState } from '../components/EmptyState'
import { FilterGroup } from '../components/FilterGroup'
import type { FilterOption } from '../components/FilterGroup'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** Which slice of the list to show. `all` means no narrowing at all. */
type Availability = 'all' | 'available' | 'unavailable'

const FILTERS: FilterOption<Availability>[] = [
  { value: 'all', label: 'shipping.filter.all' },
  { value: 'available', label: 'shipping.filter.available' },
  { value: 'unavailable', label: 'shipping.filter.unavailable' },
]

/** The `available` query value each choice means. Undefined is the "all" case,
 * and the server reads a missing parameter as "do not filter".
 */
function availableOf(filter: Availability): boolean | undefined {
  if (filter === 'all') return undefined
  return filter === 'available'
}

/**
 * What the site charges to deliver to each wilaya, as of the last sync.
 *
 * Shared reference data, like the catalogue, so every signed-in user gets it
 * rather than it being an administrator's screen.
 *
* **Unavailable wilayas are listed, not hidden.** "We do not deliver there" is
  * the answer somebody checking coverage is looking for, so the filter narrows to
  * them rather than the default dropping them — a table of only the wilayas you
  * can ship to cannot answer "can you ship to X".
  *
  * **Fetch prices is the one control here that reaches sawa9ly.app**, so it is a
  * button in the header rather than something the list does on its own: one
  * request per press, never on a render and never per row. There is deliberately
  * no equivalent for the wilayas or the communes — those are seeded reference
  * data, because the site cannot be asked for them at all, so there is nothing
  * here to fetch.
  */
export function Shipping() {
  const { t } = useI18n()
  const { invalidate } = useSession()
  const [filter, setFilter] = useState<Availability>('all')
  const [syncing, setSyncing] = useState(false)
  const [notice, setNotice] = useState('')

  const list = usePagedList<DeliveryPrice>(
    (query: ListQuery) => listPrices({ ...query, available: availableOf(filter) }),
    {
      errorKey: 'error.shipping',
      onUnauthorized: invalidate,
      // The fetcher is an inline arrow, so its identity changes every render and
      // cannot be the trigger. This is the explicit statement that a different
      // slice of the list is now wanted.
      fetcherKey: filter,
    },
  )

  const prices = list.items

  async function onSync() {
    setSyncing(true)
    list.setError('')
    setNotice('')

    try {
      const result = await syncPrices()
      setNotice(t('shipping.synced', { count: result.total }))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.shippingSync'))
    } finally {
      setSyncing(false)
    }
  }

  function onFilter(next: Availability) {
    // Back to the first page, because the page numbers belong to the slice that
    // was showing. Narrowing to three unavailable wilayas while sitting on page 2
    // would otherwise ask for rows 50+ of a result set that holds three, and show
    // an empty table with no sign of why.
    list.query.setPage(0)
    setFilter(next)
  }

  return (
    <section>
      <PageHeader title={t('shipping.title')}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onSync}
          disabled={syncing}
        >
          {syncing ? t('shipping.syncing') : t('shipping.sync')}
        </button>
      </PageHeader>

      <p className="mb-5 max-w-prose text-sm text-muted">{t('shipping.intro')}</p>

      {list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <FilterGroup
        label={t('shipping.filterLabel')}
        options={FILTERS}
        value={filter}
        onChange={onFilter}
      />

      {!prices ? (
        <MessageSpinner messageKey="loading.shipping" />
      ) : prices.length === 0 ? (
        <EmptyState>
          <p>{filter === 'all' ? t('shipping.empty') : t('shipping.emptyFiltered')}</p>
          <p className="mt-2">
            {filter === 'all' ? t('shipping.emptyFetch') : t('shipping.emptyCli')}{' '}
            <code>python main.py shipping sync --user &lt;name&gt;</code>
          </p>
        </EmptyState>
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('shipping.col.wilaya')}</th>
              <th>{t('shipping.col.wilayaId')}</th>
              <th>{t('shipping.col.available')}</th>
              <th>{t('shipping.col.price')}</th>
              <th>{t('shipping.col.officePrice')}</th>
            </tr>
          </thead>
          <tbody>
            {prices.map((price) => (
              <tr key={price.id}>
                <td className="font-medium">
                  {price.wilaya_name ?? (
                    <span className="font-mono tabular-nums text-muted">
                      {price.wilaya_id}
                    </span>
                  )}
                </td>
                <td className="font-mono text-xs text-muted tabular-nums">
                  {price.wilaya_id}
                </td>
                <td>
                  <span className={price.available ? 'badge badge-ok' : 'badge'}>
                    {price.available ? t('generic.yes') : t('generic.no')}
                  </span>
                </td>
                <td className="tabular-nums">
                  {price.available ? formatPrice(price.price) : t('shipping.notServed')}
                </td>
                <td className="tabular-nums">
                  {price.available ? formatPrice(price.office_price) : t('shipping.notServed')}
                </td>
              </tr>
            ))}
          </tbody>
        </TablePanel>
      )}

      {prices && prices.length > 0 && (
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

/**
 * A price as whole dinars, or null when the server sent none.
 *
 * The server sends a number, not the site's `'1,000 دج'`, so this is formatting
 * and nothing else. Null is passed through rather than formatted, so the caller
 * decides what a missing price reads as — and it falls back to the shared dash
 * rather than printing a zero, which is a number the site published and means
 * something different.
 */
function formatPrice(value: number | null) {
  return value === null ? null : value.toLocaleString()
}