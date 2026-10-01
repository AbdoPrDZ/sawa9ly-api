import { listQuery, request } from './client'
import type { AdminUser, ListQuery, NewUser, PageResult, UserEdits } from './types'

/** One page of users. `query.q` searches the username. */
export function listUsers(query: ListQuery = {}) {
  return request<PageResult<AdminUser>>(`/admin/users${listQuery(query)}`)
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