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
  /** Whether this user has set their own sawa9ly credentials. An admin sees the
   *  fact and not the address: they own it, and set it from their profile. */
  has_sawa9ly_credentials: boolean
  /** Which chat their notifications go to, or null. Not a credential — it is
   *  here so a super can tell somebody which chat they linked. */
  telegram_chat_id: string | null
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

/** The signed-in user's link to a Telegram chat. */
export interface TelegramBinding {
  user_id: number
  bound: boolean
  chat_id: string | null
  chat_type: string | null
  chat_title: string | null
  chat_username: string | null
  /** True while a code is outstanding, so the page can say "waiting for you to
   *  open the link" rather than showing nothing. */
  code_pending: boolean
  code_expires_at: string | null
  verified_at: string | null
  created_at: string | null
}

/** A freshly issued binding link. The code is in the clear here and nowhere
 *  else: only its hash is stored, so this response is the only time it can be
 *  read. */
export interface TelegramLink {
  username: string
  url: string
  code: string
  expires_at: string | null
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

/** Where an order has got to. Mirrors the server's `OrderState`; the server
 * decides what may move where, this only decides how to display it.
 */
export type OrderState = 'draft' | 'confirmed' | 'done' | 'cancelled'

/** One product on an order.
 *
 * `product_id` is the sawa9ly id, the same one the catalogue uses, even though
 * the server stores an internal id alongside it.
 */
export interface OrderLine {
  id: number
  product_id: number
  quantity: number
  /** The reseller's selling price. Absent means it was never set, which is not
   * the same as zero, so it stays nullable here.
   */
  price: number | null
  /** The product's own price, snapshotted when the line was created. Null when
   * the product had no parsable price at that moment — never re-read from the
   * product afterwards, so a later price change cannot rewrite the order's
   * history.
   */
  origin_price: number | null
  subtotal: number
  title: string | null
  /** A remark about this line only. The site never sees it. */
  note: string | null
}

/** An order, with its lines in full. */
export interface Order {
  id: number
  state: OrderState
  client_id: number | null
  /** The site's own order number, set once the order is submitted. */
  reference: string | null
  note: string | null
  total: number
  lines: OrderLine[]
  created_at: string | null
  /** The owner's username. Only the super-only admin listing sends it, because
   * that is the one view spanning more than one user.
   */
  username?: string | null
}

/** A delivery recipient one of the signed-in user's orders can be shipped to.
 *
 * The field names are the site's, not ours: `adresse` and `wilaya_id` come
 * straight off its checkout form, which is the whole point of storing them.
 */
export interface Client {
  id: number
  user_id: number
  full_name: string
  phone: string | null
  adresse: string | null
  wilaya_id: number | null
  commune_id: number | null
  note: string | null
}

/** What a new or updated client needs. `full_name` is the only required field. */
export interface NewClient {
  full_name: string
  phone?: string | null
  adresse?: string | null
  wilaya_id?: number | null
  commune_id?: number | null
  note?: string | null
}

/** Where a landing page is in its life. Mirrors the server's `PageState`. */
export type PageState = 'draft' | 'publish' | 'archive'

/** One of the signed-in user's landing pages.
 *
 * `product_id` is our own `products.id`, which is what a line is keyed by, so it
 * is not the number to show a person. The sawa9ly id comes back separately as
 * `sawa9ly_product_id`; use that one in a link or a lookup.
 */
export interface Page {
  id: number
  user_id: number
  product_id: number
  sawa9ly_product_id: number | null
  product_title: string | null
  /** The token the page is served under. Not the row id, which is enumerable. */
  public_id: string
  title: string
  html: string
  state: PageState
  created_at: string | null
  updated_at: string | null
}

/** A new page. The product is named by its sawa9ly id, as everywhere else. */
export interface NewPage {
  product_id: number
  title: string
  html?: string
}

/** A change to a page. Absent means unchanged — note that `html: ''` clears it. */
export interface PageEdits {
  title?: string
  html?: string
  state?: PageState
}

/** The editable part of a user. Every field is optional: absent means unchanged. */
export interface UserEdits {
  role?: Role
  /** The dashboard login password. Deliberately the only thing an admin may set
   *  — a user sets their own sawa9ly credentials, and an admin who could type
   *  them in could act as that user on the site. */
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
