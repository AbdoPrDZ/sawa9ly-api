import { request } from './client'
import type { LoginResponse, SessionUser } from './types'

/** Sign in. The caller stores the token; this only exchanges it. */
export function login(username: string, password: string) {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

/** The signed-in user, or throws so the app can send them back to the login. */
export function me() {
  return request<SessionUser>('/auth/me')
}