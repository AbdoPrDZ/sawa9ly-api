import type { Page } from '../../api/types'

/** The public address of a page, built from wherever the dashboard is served.
 *
 * The origin is read rather than written down because the dashboard runs on a
 * different port in development (Vite) than in production (the API), and the
 * page has to be reachable at whatever host a visitor would actually use.
 *
 * The path is the server's public route, not this file's opinion of it.
 */
export function publicUrl(page: Page): string {
  return `${window.location.origin}/pages/${page.public_id}`
}
