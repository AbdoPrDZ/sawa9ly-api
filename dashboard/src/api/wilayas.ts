import { request } from './client'
import type { Commune, Wilaya } from './types'

/**
 * The 58 wilayas and their 1541 communes.
 *
 * Reference data seeded from the site's own commune select, so both of these read
 * the local database and never reach sawa9ly.app.
 *
 * `listCommunes` is filtered by wilaya because that pairing is the question a form
 * actually asks, and because the site cannot answer it: it has no commune list page
 * and no search, so which communes belong to a wilaya is not something a scrape
 * could read off a page. Called with `null` it answers with all of them, which is
 * a usable answer to "every commune" and a useless one to "the communes of the
 * wilaya somebody just picked".
 */

/** The 58 wilayas. Small and fixed between syncs, so never paged. */
export function listWilayas() {
  return request<Wilaya[]>('/shipping/wilayas')
}

/**
 * One wilaya's communes, or all 1541 when `wilayaId` is null.
 *
 * The id goes in the query string by hand rather than through `listQuery`, which
 * exists to build a list screen's search box and pager and knows nothing about
 * this. There is no `q` and no paging on either route.
 */
export function listCommunes(wilayaId: number | null) {
  const path = wilayaId === null ? '/shipping/communes' : `/shipping/communes?wilaya_id=${wilayaId}`

  return request<Commune[]>(path)
}