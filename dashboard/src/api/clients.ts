import { listQuery, request } from './client'
import type { Client, ListQuery, NewClient, PageResult } from './types'

/** The signed-in user's delivery recipients.
 *
 * The server scopes every route here to the caller, so this is one user's
 * clients whichever credential presented them.
 */

/** One page of recipients. `query.q` searches the name and the phone number. */
export function listClients(query: ListQuery = {}) {
  return request<PageResult<Client>>(`/clients${listQuery(query)}`)
}

/**
 * Add a client, or update the one already stored under the same name.
 *
 * The name is the key: posting an existing `full_name` updates that row rather
 * than creating a second recipient, and only the fields sent with a value are
 * written, so a blank box leaves the stored one alone.
 */
export function createClient(input: NewClient) {
  return request<Client>('/clients', { method: 'POST', body: JSON.stringify(input) })
}
