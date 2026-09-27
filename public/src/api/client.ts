/** Transport: one place that attaches the token, and one place errors are
 * turned into a message the UI can show.
 *
 * Paths are relative on purpose. The dashboard is served from the same origin
 * as the API, so there is no base URL to configure and no CORS to arrange; the
 * dev proxy in vite.config.ts exists only to reproduce that locally.
 */

const TOKEN_KEY = 'sawa9ly.dashboard.token'

/** Carries the HTTP status, so callers can tell "signed out" from "not allowed". */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** True when the caller needs to sign in again or has no business asking. */
export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

export const token = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  },
  set(value: string) {
    localStorage.setItem(TOKEN_KEY, value)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
  },
}

/**
 * Pull a readable message out of a FastAPI error body.
 *
 * `detail` is a string for the raises in this project but a list for validation
 * errors, so both shapes are handled.
 */
function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail

    if (typeof detail === 'string') return detail

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
  }

  return fallback
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) }
  const current = token.get()

  if (current) headers['Authorization'] = `Bearer ${current}`
  if (init.body) headers['Content-Type'] = 'application/json'

  const response = await fetch(path, { ...init, headers })

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let body: unknown = null

  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, detailOf(body, `Request failed (${response.status}).`))
  }

  return body as T
}
