import { request } from './client'
import type { Profile, ProfileIn } from './types'

/** The signed-in user's own account. */
export function getProfile() {
  return request<Profile>('/auth/me/profile')
}

/**
 * Change part of your own account.
 *
 * `ProfileIn` is partial by design — the API treats an absent key as "unchanged"
 * — so this takes the whole body and the caller sends only what it edited. That
 * is the contract the profile form has always had; the language is just another
 * field on it.
 */
export function updateProfile(input: Partial<ProfileIn>) {
  return request<Profile>('/auth/me/profile', {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

/** Ask the site for a sawa9ly session for this account. */
export function sawa9lyLogin() {
  return request<{ success: boolean; message: string }>('/auth/me/sawa9ly-login', {
    method: 'POST',
  })
}
