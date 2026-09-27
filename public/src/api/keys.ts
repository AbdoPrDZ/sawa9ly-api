import { request } from './client'
import type { AdminApiKey } from './types'

export function listKeys() {
  return request<AdminApiKey[]>('/admin/api-keys')
}

/** Issue a key. The returned `key` is the only time the plaintext exists. */
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