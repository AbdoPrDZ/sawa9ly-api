import { request } from './client'
import type { Tracker } from './types'

/** A user's own watches, managed from the dashboard. */

export function listTrackers() {
  return request<Tracker[]>('/trackers')
}

/** Starts watching. Watching something already watched is not an error. */
export function watch(productId: number) {
  return request<Tracker & { created: boolean }>('/trackers', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  })
}

export function unwatch(productId: number) {
  return request<{ unwatched: number }>('/trackers', {
    method: 'DELETE',
    body: JSON.stringify({ product_id: productId }),
  })
}
