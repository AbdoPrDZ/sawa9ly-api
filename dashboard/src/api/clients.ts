import { request } from './client'
import type { Client, NewClient } from './types'

/** The signed-in user's delivery recipients.
 *
 * The server scopes every route here to the caller, so this is one user's
 * clients whichever credential presented them.
 */

export function listClients() {
  return request<Client[]>('/clients')
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
