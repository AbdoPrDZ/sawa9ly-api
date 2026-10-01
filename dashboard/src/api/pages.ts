import { listQuery, request } from './client'
import type { ListQuery, NewPage, Page, PageEdits, PageResult } from './types'

/** The signed-in user's own landing pages, for the catalogue's products.
 *
 * The server scopes every route here to the caller, so this is one user's pages
 * whichever credential presented them. `product_id` on the way in is the sawa9ly
 * id; on the way out it is ours, with the sawa9ly one alongside it.
 */

/** One page of your pages. `query.q` searches the title and the product id. */
export function listPages(query: ListQuery = {}) {
  return request<PageResult<Page>>(`/pages${listQuery(query)}`)
}

export function getPage(pageId: number) {
  return request<Page>(`/pages/${pageId}`)
}

/** Start a draft page. A user may keep several pages for the same product. */
export function createPage(input: NewPage) {
  return request<Page>('/pages', { method: 'POST', body: JSON.stringify(input) })
}

/** Change a page. Fields left out are untouched, so a title-only edit is safe. */
export function updatePage(pageId: number, edits: PageEdits) {
  return request<Page>(`/pages/${pageId}`, { method: 'PATCH', body: JSON.stringify(edits) })
}
