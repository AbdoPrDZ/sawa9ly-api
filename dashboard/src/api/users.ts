import { request } from './client'
import type { AdminUser, NewUser, UserEdits } from './types'

export function listUsers() {
  return request<AdminUser[]>('/admin/users')
}

export function createUser(input: NewUser) {
  return request<AdminUser>('/admin/users', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateUser(id: number, edits: UserEdits) {
  return request<AdminUser>(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(edits),
  })
}

export function deleteUser(id: number) {
  return request<{ deleted: string }>(`/admin/users/${id}`, { method: 'DELETE' })
}