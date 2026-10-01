import { useNavigate } from 'react-router-dom'
import { listAllOrders, listOrders } from '../api/orders'
import type { Order } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { EmptyState } from '../components/EmptyState'
import { OrderStateBadge } from '../components/OrderStateBadge'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** Orders, newest first.
 *
 * A `super` sees every user's orders, because this is the one view that has to
 * answer "what has been ordered across the whole installation". Everyone else
 * sees their own, which is what `/v1/orders` already scopes to.
 *
 * Read-only in both cases, because a checkout places a real order on the site
 * that cannot be withdrawn from here. Building and placing an order stays with
 * the CLI and the API, where the working directory and the live cart are in
 * reach.
 */
export function Orders() {
  const { user, invalidate } = useSession()
  const { t } = useI18n()
  const navigate = useNavigate()

  const isSuper = user?.role === 'super'

  const list = usePagedList<Order>(isSuper ? listAllOrders : listOrders, {
    errorKey: 'error.orders',
    onUnauthorized: invalidate,
    fetcherKey: isSuper ? 'all' : 'own',
  })
  const orders = list.items

  return (
    <section>
      <PageHeader title={t('orders.title')}>
        {isSuper ? <span className="text-xs text-muted">{t('orders.everyone')}</span> : null}
      </PageHeader>

      {isSuper ? <Banner kind="info">{t('orders.superBanner')}</Banner> : null}

{list.error ? <Banner kind="error">{list.error}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.orders') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!orders ? (
        <MessageSpinner messageKey="loading.orders" />
      ) : orders.length === 0 ? (
        <EmptyState>
          {list.query.q ? (
            <p>{t('orders.emptySearch')}</p>
          ) : isSuper ? (
            <p>{t('orders.emptyAll')}</p>
          ) : (
            <>
              <p>{t('orders.empty')}</p>
              <AdminOnly>
                <p className="mt-2">
                  {t('orders.emptyCli')}{' '}
                  <code>python main.py order create --user &lt;name&gt;</code>
                </p>
              </AdminOnly>
            </>
          )}
        </EmptyState>
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('orders.col.id')}</th>
              {isSuper ? <th>{t('orders.col.user')}</th> : null}
              <th>{t('orders.col.created')}</th>
              <th>{t('orders.col.state')}</th>
              <th>{t('orders.col.client')}</th>
              <th>{t('orders.col.reference')}</th>
              <th>{t('orders.col.lines')}</th>
<th>{t('orders.col.total')}</th>
            </tr>
          </thead>
          <tbody>
{orders.map((order) => (
              <tr
                key={order.id}
                className="cursor-pointer"
                onClick={() => navigate(`/orders/${order.id}`)}
              >
                <td className="font-mono text-xs text-muted">{order.id}</td>
                {isSuper ? <td className="font-medium">{order.username ?? t('generic.unknown')}</td> : null}
                <td className="text-muted">{order.created_at ?? t('generic.unknown')}</td>
                <td>
                  <OrderStateBadge state={order.state} />
                </td>
                <td>{order.client_id ?? t('generic.unknown')}</td>
                <td className="font-mono text-xs">{order.reference ?? t('generic.unknown')}</td>
                <td className="text-muted">{order.lines.length}</td>
<td className="font-medium">{order.total}</td>
              </tr>
            ))}
</tbody>
        </TablePanel>
      )}

      {orders && orders.length > 0 && (
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

