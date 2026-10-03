import { listQuery, request } from './client'
import type { DeliveryPrice, ListQuery, PageResult } from './types'

/**
 * The site's delivery prices, per wilaya.
 *
 * One list for everybody, so nothing here is scoped to the caller — the server
 * publishes it once and a sync by any user is read by all of them. The routes
 * still need a credential; that decides who may read it and whose sawa9ly session
 * a sync scrapes with, never whose rows are touched.
 */

/**
 * One page of saved prices.
 *
 * `query.available` narrows to the wilayas the site does serve, or to the ones it
 * does not. Left out, the answer covers every wilaya. There is no `q` here: the
 * route has no text search, so a term would be sent and ignored, which looks like
 * a search that half works.
 */
export function listPrices(query: ListQuery = {}) {
  return request<PageResult<DeliveryPrice>>(`/shipping${listQuery(query)}`)
}