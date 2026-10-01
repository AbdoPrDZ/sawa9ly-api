import { listQuery, request } from './client'
import type { ListQuery, Order, PageResult } from './types'

/** A user's own orders.
 *
 * Read-only here on purpose. The routes behind these also edit lines and check
 * out, and a checkout places a real order on the site that cannot be withdrawn
 * from here, so that stays with the CLI and the API.
 */

/** One page of your own orders. `query.q` searches the order id and reference. */
export function listOrders(query: ListQuery = {}) {
  return request<PageResult<Order>>(`/orders${listQuery(query)}`)
}

export function getOrder(orderId: number) {
  return request<Order>(`/orders/${orderId}`)
}

/**
 * Every user's orders. Super only, and a dashboard token only — an API key is
 * not accepted here, because this is the view that crosses user boundaries.
 *
 * Separate from `listOrders` rather than a flag on it: the two answer different
 * questions and need different credentials, and the caller has to be able to
 * tell which one it is asking for.
 */
export function listAllOrders(query: ListQuery = {}) {
  return request<PageResult<Order>>(`/admin/orders${listQuery(query)}`)
}

/** One order, whoever owns it. Super only. */
export function getAnyOrder(orderId: number) {
  return request<Order>(`/admin/orders/${orderId}`)
}
