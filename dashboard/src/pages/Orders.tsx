import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isUnauthorized } from '../api/client'
import { listAllOrders, listOrders } from '../api/orders'
import type { Order } from '../api/types'
import { Banner } from '../components/Banner'
import { OrderStateBadge } from '../components/OrderStateBadge'
import { Spinner } from '../components/Spinner'
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
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [error, setError] = useState('')

  const isSuper = user?.role === 'super'

  const load = useCallback(async () => {
    try {
      setOrders(isSuper ? await listAllOrders() : await listOrders())
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(message(caught, 'Could not load the orders.'))
    }
  }, [isSuper, invalidate])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <section>
      <div className="section-head">
        <h2>Orders</h2>
      </div>

      {isSuper ? (
        <Banner kind="info">
          Showing every user's orders, because you are a super. Editing or checking
          out somebody else's order stays a CLI operation on their own account.
        </Banner>
      ) : null}

      {error ? <Banner kind="error">{error}</Banner> : null}

      {!orders ? (
        <Spinner label="Loading orders" />
      ) : orders.length === 0 ? (
        isSuper ? (
          <p className="muted">No orders from anybody yet.</p>
        ) : (
          <p className="muted">
            No orders yet. Start one with{' '}
            <code>python main.py order create --user &lt;name&gt;</code>.
          </p>
        )
      ) : (
        <table>
          <thead>
            <tr>
              <th>Id</th>
              {isSuper ? <th>User</th> : null}
              <th>Created</th>
              <th>State</th>
              <th>Client</th>
              <th>Reference</th>
              <th>Lines</th>
              <th>Total</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>{order.id}</td>
                {isSuper ? <td>{order.username ?? '—'}</td> : null}
                <td className="muted">{order.created_at ?? '—'}</td>
                <td>
                  <OrderStateBadge state={order.state} />
                </td>
                <td>{order.client_id ?? '—'}</td>
                <td>{order.reference ?? '—'}</td>
                <td className="muted">{order.lines.length}</td>
                <td>{order.total}</td>
                <td className="row-actions">
                  <Link className="ghost link" to={`/orders/${order.id}`}>
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
