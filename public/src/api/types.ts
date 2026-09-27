/** Shapes the admin API returns. Kept apart from the client so a response
 * change has one place to change, and so the client has no knowledge of what it
 * is fetching.
 */

/** The roles the dashboard can offer. The root role is deliberately not among
 * them: it is assigned from the environment, never chosen here.
 */
export type Role = 'admin' | 'user'

/** The full set the API understands, for displaying a user's actual role. */
export type AnyRole = Role | 'super'


export interface SessionUser {
  id: number
  username: string
  role: AnyRole
  is_admin: boolean
}

export interface LoginResponse {
  token: string
  token_type: string
  expires_in: number
  user: SessionUser
}

export interface AdminUser {
  id: number
  username: string
  role: AnyRole
  is_admin: boolean
  /** False for a `super`: the dashboard may not change or delete it. */
  can_be_managed: boolean
  sawa9ly_email: string | null
  has_sawa9ly_credentials: boolean
  can_log_in: boolean
  active_api_keys: number
  clients: number
  orders: number
  created_at: string | null
}

/** The signed-in user's own account. */
export interface Profile {
  id: number
  username: string
  role: AnyRole
  is_admin: boolean
  can_log_in: boolean
  has_sawa9ly_credentials: boolean
  sawa9ly_email: string | null
  has_sawa9ly_session: boolean
}

export interface Sawa9lyLoginResult {
  success: boolean
  username: string
  message: string
  has_session: boolean
}

/** A saved catalogue product. */
export interface CatalogueProduct {
  product_id: number
  title: string | null
  price: string | null
  description: string | null
  images: string[]
  figures: string[]
  categories: string[]
  available: boolean
}

/** A user's subscription to a watched product. */
export interface Tracker {
  id: number
  user_id: number
  target_model: string
  target_id: number
  created_at: string | null
  last_checked_at: string | null
  last_changed_at: string | null
  /** The watched product, resolved for display. */
  target: CatalogueProduct | null
}

/** The editable part of a user. Every field is optional: absent means unchanged. */
export interface UserEdits {
  role?: Role
  sawa9ly_email?: string
  sawa9ly_password?: string
  password?: string
}

export interface NewUser extends UserEdits {
  username: string
}

export interface AdminApiKey {
  id: number
  user_id: number
  username: string | null
  prefix: string
  label: string | null
  revoked: boolean
  usable: boolean
  created_at: string | null
  last_used_at: string | null
  expires_at: string | null
  /** Present only in the response that created it. */
  key?: string | null
}
