import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { isUnauthorized } from '../api/client'
import { getAnyOrder, getOrder } from '../api/orders'
import type { Order } from '../api/types'
import { Banner } from '../components/Banner'
import { OrderStateBadge } from '../components/OrderStateBadge'
import { PageHeader } from '../components/PageHeader'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
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
  const { t } = useI18n()
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState('')

  const id = Number(orderId)
  const isSuper = user?.role === 'super'

  const load = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError(t('error.orderId', { id: orderId ?? '' }))
      return
    }

    setError('')

    try {
      setOrder(isSuper ? await getAnyOrder(id) : await getOrder(id))
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(apiErrorMessage(caught, t, 'error.order'))
    }
  }, [id, orderId, isSuper, invalidate, t])

  useEffect(() => {
    void load()
  }, [load])

  if (!order) {
    return error ? (
      <section>
        <Banner kind="error">{error}</Banner>
      </section>
    ) : (
      <MessageSpinner messageKey="loading.order" fields={{ id: orderId ?? '' }} />
    )
  }

  return (
    <section>
      <PageHeader title={t('order.title', { id: order.id })}>
        <OrderStateBadge state={order.state} />
        <Link className="btn-link" to="/orders">
          {t('order.back')}
        </Link>
      </PageHeader>

      {error ? <Banner kind="error">{error}</Banner> : null}

      {order.state === 'draft' ? <Banner kind="info">{t('order.draftBanner')}</Banner> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="card">
          <h3 className="mb-4">{t('order.details')}</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
            <Fact label={t('order.factState')}>
              <OrderStateBadge state={order.state} />
            </Fact>
            {order.username ? <Fact label={t('order.factBy')}>{order.username}</Fact> : null}
            <Fact label={t('order.factCreated')}>{order.created_at ?? t('generic.unknown')}</Fact>
            <Fact label={t('order.factClient')}>{order.client_id ?? t('generic.unknown')}</Fact>
            <Fact label={t('order.factReference')}>
              {order.reference ?? t('order.notSubmitted')}
            </Fact>
            <Fact label={t('order.factTotal')}>
              <span className="font-medium">{order.total}</span>
            </Fact>
          </dl>
        </div>

        {order.note ? (
          <div className="card">
            <h3 className="mb-3">{t('order.note')}</h3>
            <p className="max-h-80 overflow-auto text-sm whitespace-pre-wrap text-muted">
              {order.note}
            </p>
          </div>
        ) : null}
      </div>

      <div className="mt-4">
        <TablePanel>
          <thead>
            <tr>
              <th>{t('order.col.product')}</th>
              <th>{t('order.col.title')}</th>
              <th>{t('order.col.quantity')}</th>
              {/*
                Origin price sits immediately before Price, so the difference
                between them — the margin this line was built at — is readable
                across two columns rather than needing arithmetic.

                It is the product's own price as it was when the line was created,
                not today's, so it does not move when the site changes price.
                `—` means it was never known: the product was not in the
                catalogue at the time, or its price carried no number.
              */}
              <th>{t('order.col.origin')}</th>
              <th>{t('order.col.price')}</th>
              <th>{t('order.col.subtotal')}</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.id}>
                <td>
                  <Link className="btn-link" to={`/products/${line.product_id}`}>
                    {line.product_id}
                  </Link>
                </td>
                <td className="max-w-xs truncate font-medium">
                  {line.title ?? t('generic.unknown')}
                </td>
                <td>{line.quantity}</td>
                <td className={line.origin_price === null ? 'text-muted' : undefined}>
                  {line.origin_price ?? t('generic.unknown')}
                </td>
                <td>{line.price ?? t('generic.unknown')}</td>
                <td className="font-medium">{line.subtotal}</td>
              </tr>
            ))}
            {order.lines.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-10 text-center text-muted">
                  {t('order.noLines')}
                </td>
              </tr>
            ) : null}
          </tbody>
        </TablePanel>
      </div>
    </section>
  )
}

/** One label and its value, stacked so a two-column grid of them stays aligned. */
function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="mb-1 text-[0.6875rem] font-medium tracking-wider text-faint uppercase">
        {label}
      </dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

