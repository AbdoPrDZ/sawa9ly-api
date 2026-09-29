/** Transport: one place that attaches the token, and one place errors are
 * turned into a message the UI can show.
 *
 * Paths are relative on purpose. The dashboard is served from the same origin
 * as the API, so there is no base URL to configure and no CORS to arrange; the
 * dev proxy in vite.config.ts exists only to reproduce that locally.
 */

/**
 * Where the dashboard itself is served from.
 *
 * Read by the router in `main.tsx`, so every route and `Link` in the app can
 * stay relative. It has to be the same string as `DASHBOARD_BASE` in
 * `src/server.py` and `base` in `vite.config.ts`; those three are the only
 * places the prefix is written down.
 */
export const BASENAME = '/dashboard'

/**
 * The outer namespace every API route sits under, matching `API_BASE` in
 * `src/server.py`. Kept separate from the version prefix below so the two
 * concerns stay separable: this is where the API lives, that is which contract
 * version of it you are calling.
 */
const API_BASE = '/api'

/**
 * The API contract version, matching `API_PREFIX` in `src/server.py`.
 *
 * Applied here rather than in each caller so the resource modules stay
 * prefix-agnostic: a `/api/v2` is this one constant, not fourteen edits. Callers
 * pass the bare resource path, e.g. `request('/auth/me')`.
 */
const API_PREFIX = `${API_BASE}/v1`

/**
 * Bare resource prefixes the server mounts without the version prefix.
 *
 * `/api/health` and `/api/me` are unversioned too, and deliberately absent:
 * nothing in the dashboard calls them. Adding one here rather than calling it
 * wrongly is the point.
 *
 * These are matched against the path the caller passed, which is the bare
 * resource path, so the list must not carry the `API_BASE` prefix.
 *
 * Keep in step with the unversioned mounts in `create_app` in `src/server.py`.
 * The server is the authority; this is the client half of the same fact.
 */
const UNVERSIONED = ['/auth', '/admin']

/** Resolve a bare resource path to the URL to actually fetch. */
function urlFor(path: string): string {
  const unversioned = UNVERSIONED.some((prefix) => path.startsWith(prefix))

  return unversioned ? API_BASE + path : API_PREFIX + path
}

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

/**
 * Why a 200 that is not JSON is a problem rather than an empty result.
 *
 * The dashboard shell is served from a catch-all route, so a request for an API
 * path the running server does not have comes back as `index.html` with a 200.
 * Returning that as `null` would be indistinguishable from "no data", and a
 * page holding its rows in state would sit on its loading spinner for ever with
 * nothing to show. Naming the cause is the whole point: this nearly always means
 * the server is running older code than the dashboard expects.
 */
const NOT_JSON =
  'The server sent a web page instead of data. It most likely does not have this ' +
  'route — restart it so it picks up the latest code.'

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) }
  const current = token.get()

  if (current) headers['Authorization'] = `Bearer ${current}`
  if (init.body) headers['Content-Type'] = 'application/json'

  const response = await fetch(urlFor(path), { ...init, headers })

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let body: unknown = null
  let parsed = true

  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      parsed = false
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, detailOf(body, `Request failed (${response.status}).`))
  }

  if (!parsed) throw new Error(NOT_JSON)

  return body as T
}
