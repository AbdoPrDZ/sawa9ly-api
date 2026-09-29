import { request } from './client'
import type { TelegramBinding, TelegramLink } from './types'

/** Self-service: the signed-in user's own Telegram chat. Available at any role,
 *  and always the caller's own — there is no route that links somebody else's.
 *
 *  Bare resource paths, like every other module here: `request` adds `/api/v1`
 *  itself, so writing `/v1/telegram` would ask for `/api/v1/v1/telegram`.
 */

export function getBinding() {
  return request<TelegramBinding>('/telegram')
}

/** A `t.me` link that binds the caller's chat when opened. The code is in the
 *  clear in this response and nowhere else, so it is shown once and not kept.
 */
export function issueLink() {
  return request<TelegramLink>('/telegram/link', { method: 'POST' })
}

/** Stop sending notifications, and let a different chat be linked. */
export function unbind() {
  return request<{ unbound: string }>('/telegram', { method: 'DELETE' })
}

/** Send a test message to the caller's own chat, to check the link delivers.
 *  The same operation as `python main.py telegram test`. */
export function sendTest() {
  return request<{ sent: boolean; chat_id: string }>('/telegram/test', { method: 'POST' })
}
