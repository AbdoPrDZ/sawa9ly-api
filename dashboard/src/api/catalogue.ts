import { listQuery, request } from './client'
import type { CatalogueProduct, ListQuery, PageResult } from './types'

/** The saved catalogue. Reading is open; saving scrapes the live site. */

/** One page of saved products. `query.q` searches the sawa9ly id and the title. */
export function listProducts(query: ListQuery = {}) {
  return request<PageResult<CatalogueProduct>>(`/catalogue${listQuery(query)}`)
}

export function getProduct(productId: number) {
  return request<CatalogueProduct>(`/catalogue/${productId}`)
}

/**
 * Scrape a product page from the site and store it.
 *
 * This is the only call here that reaches the live site, so it is slow by
 * nature and worth doing deliberately rather than on a list refresh.
 */
export function saveProduct(productId: number) {
  return request<CatalogueProduct>(`/catalogue/${productId}`, { method: 'POST' })
}
