import type { OrderState } from '../api/types'

/** How each state reads.
 *
 * Every state is named here rather than falling through to a default, because a
 * state added on the server and not here would otherwise be drawn as `done` —
 * the one badge that means "finished, all fine". A cancelled order is not that.
 */
const BADGES: Record<OrderState, string> = {
  draft: 'badge',
  confirmed: 'badge badge-confirmed',
  done: 'badge badge-active',
  cancelled: 'badge badge-cancelled',
}

/** Where an order has got to, as a badge.
 *
 * The four states mean different things to the reader, so they read
 * differently: a draft is still being built, a confirmed one is on the site, a
 * done one is finished and a cancelled one was called off. The server decides
 * which state an order may move to; this only says what the one it has looks
 * like.
 */
export function OrderStateBadge({ state }: { state: OrderState }) {
  return <span className={BADGES[state]}>{state}</span>
}
