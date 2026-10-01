import { listQuery, request } from './client'
import type { AdminApiKey, ListQuery, PageResult } from './types'

/** The signed-in user's own keys. Every account may do this for itself. */

/** One page of your keys. `query.q` searches the key prefix and the label. */
export function listMyKeys(query: ListQuery = {}) {
  return request<PageResult<AdminApiKey>>(`/keys${listQuery(query)}`)
}

/** Issue a key for yourself. The returned `key` is the only time the plaintext
 * exists.
 *
 * Separate from `createKey` below because they are different operations, not one
 * operation with a different argument: this has no user in it at all, so it
 * cannot be pointed at somebody else.
 */
export function createMyKey(label?: string, expiresInDays?: number) {
  return request<AdminApiKey>('/keys', {
    method: 'POST',
    body: JSON.stringify({
      label: label || null,
      expires_in_days: expiresInDays ?? null,
    }),
  })
}

/** Revoke one of your own keys. Somebody else's is a 404, not a 403. */
export function revokeMyKey(id: number) {
  return request<{ revoked: string }>(`/keys/${id}`, { method: 'DELETE' })
}

/** Every key for every user. Administrator only. */
export function listKeys(query: ListQuery = {}) {
  return request<PageResult<AdminApiKey>>(`/admin/api-keys${listQuery(query)}`)
}

/** Issue a key in another user's name. `super` only. */
export function createKey(userId: number, label?: string, expiresInDays?: number) {
  return request<AdminApiKey>(`/admin/users/${userId}/api-keys`, {
    method: 'POST',
    body: JSON.stringify({
      label: label || null,
      expires_in_days: expiresInDays ?? null,
    }),
  })
}

export function revokeKey(id: number) {
  return request<{ revoked: string }>(`/admin/api-keys/${id}`, { method: 'DELETE' })
}
