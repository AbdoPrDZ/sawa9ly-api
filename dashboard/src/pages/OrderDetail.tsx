import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { isUnauthorized } from '../api/client'
import { getAnyOrder, getOrder } from '../api/orders'
import type { Order } from '../api/types'
import { Banner } from '../components/Banner'
import { OrderStateBadge } from '../components/OrderStateBadge'
import { Spinner } from '../components/Spinner'
import { useSession } from '../session/useSession'

/** One order, with its lines.
 *
 * Read-only, like the list: a draft is left as it is found rather than edited
 * here, because checking one out is the step that cannot be undone.
 *
 * A `super` reads through `/admin/orders`, which reaches any user's order, so
 * the row they opened from the all-users listing resolves. Everyone else reads
 * their own, and gets a 404 for anybody else's.
 */
export function OrderDetail() {
  const { orderId } = useParams()
  const { user, invalidate } = useSession()
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState('')

  const id = Number(orderId)
  const isSuper = user?.role === 'super'

  const load = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError(`'${orderId}' is not an order id.`)
      return
    }

    setError('')

    try {
      setOrder(isSuper ? await getAnyOrder(id) : await getOrder(id))
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(caught instanceof Error ? caught.message : 'Could not load the order.')
    }
  }, [id, orderId, isSuper, invalidate])

  useEffect(() => {
    void load()
  }, [load])

  if (!order) {
    return error ? (
      <section>
        <Banner kind="error">{error}</Banner>
      </section>
    ) : (
      <Spinner label={`Loading order ${orderId}`} />
    )
  }

  return (
    <section>
      <div className="section-head">
        <h2>Order {order.id}</h2>
        <div className="section-actions">
          <OrderStateBadge state={order.state} />
          <Link className="ghost link" to="/orders">
            Back
          </Link>
        </div>
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}

      {order.state === 'draft' ? (
        <Banner kind="info">
          This order is still a draft. Its lines can be changed and it can be submitted to
          sawa9ly from the CLI or the API.
        </Banner>
      ) : null}

      <div className="cards">
        <div className="card">
          <h3>Details</h3>
          <dl className="facts">
            <dt>State</dt>
            <dd>
              <OrderStateBadge state={order.state} />
            </dd>
            {order.username ? (
              <>
                <dt>Ordered by</dt>
                <dd>{order.username}</dd>
              </>
            ) : null}
            <dt>Created</dt>
            <dd>{order.created_at ?? '—'}</dd>
            <dt>Client</dt>
            <dd>{order.client_id ?? '—'}</dd>
            <dt>Reference</dt>
            <dd>{order.reference ?? 'not submitted'}</dd>
            <dt>Total</dt>
            <dd>{order.total}</dd>
          </dl>
        </div>

        {order.note ? (
          <div className="card">
            <h3>Note</h3>
            <p className="description">{order.note}</p>
          </div>
        ) : null}
      </div>

      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Title</th>
            <th>Quantity</th>
            <th>Origin price</th>
            <th>Price</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {order.lines.map((line) => (
            <tr key={line.id}>
              <td>
                <Link className="link" to={`/products/${line.product_id}`}>
                  {line.product_id}
                </Link>
              </td>
              <td>{line.title ?? '—'}</td>
              <td>{line.quantity}</td>
              {/*
                Origin price sits immediately before Price, so the difference
                between them — the margin this line was built at — is readable
                across two columns rather than needing arithmetic.

                It is the product's own price as it was when the line was
                created, not today's, so it does not move when the site changes
                price. `—` means it was never known: the product was not in the
                catalogue at the time, or its price carried no number.
              */}
              <td className={line.origin_price === null ? 'muted' : undefined}>
                {line.origin_price ?? '—'}
              </td>
              <td>{line.price ?? '—'}</td>
              <td>{line.subtotal}</td>
            </tr>
          ))}
          {order.lines.length === 0 ? (
            <tr>
              <td colSpan={6} className="muted">
                No lines.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  )
}
