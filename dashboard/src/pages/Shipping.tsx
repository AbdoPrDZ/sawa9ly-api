import { useState } from 'react'
import { listPrices } from '../api/shipping'
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
 * There is no sync button here on purpose: this screen reads what has been
 * scraped and does not reach the site. Refreshing the prices is a CLI or API call,
 * so nothing in a list screen can cost a request to sawa9ly.
 */
export function Shipping() {
  const { t } = useI18n()
  const { invalidate } = useSession()
  const [filter, setFilter] = useState<Availability>('all')

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
      <PageHeader title={t('shipping.title')} />

      <p className="mb-5 max-w-prose text-sm text-muted">{t('shipping.intro')}</p>

      {list.error ? <Banner kind="error">{list.error}</Banner> : null}

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
            {t('shipping.emptyCli')}{' '}
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