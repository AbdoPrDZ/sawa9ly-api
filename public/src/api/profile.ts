import { request } from './client'
import type { Profile, Sawa9lyLoginResult } from './types'

/** Self-service: the signed-in user's own account. Available at any role. */

export function getProfile() {
  return request<Profile>('/auth/me/profile')
}

/** Only the fields present are changed, so send just what was edited. */
export function updateProfile(input: {
  sawa9ly_email?: string
  sawa9ly_password?: string
  password?: string
}) {
  return request<Profile>('/auth/me/profile', {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

/** Log in to sawa9ly for this account, or refresh that session. */
export function sawa9lyLogin() {
  return request<Sawa9lyLoginResult>('/auth/me/sawa9ly-login', { method: 'POST' })
}
