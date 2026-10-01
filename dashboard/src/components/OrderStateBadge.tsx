import { useI18n } from '../i18n/useI18n'
import type { OrderState } from '../api/types'

/** How each state reads.
 *
 * Every state is named here rather than falling through to a default, because a
 * state added on the server and not here would otherwise be drawn as `done` —
 * the one badge that means "finished, all fine". A cancelled order is not that.
 */
const BADGES: Record<OrderState, string> = {
  draft: 'badge',
  confirmed: 'badge badge-accent',
  done: 'badge badge-ok',
  cancelled: 'badge badge-danger',
}

const KEYS: Record<OrderState, string> = {
  draft: 'orders.state.draft',
  confirmed: 'orders.state.confirmed',
  done: 'orders.state.done',
  cancelled: 'orders.state.cancelled',
}

/** Where an order has got to, as a badge.
 *
 * The four states mean different things to the reader, so they read differently:
 * a draft is still being built, a confirmed one is on the site, a done one is
 * finished and a cancelled one was called off. The server decides which state an
 * order may move to; this only says what the one it has looks like.
 *
 * Both maps are complete over `OrderState` on purpose, so a new state added on
 * the server fails the build here rather than rendering as `done` in every
 * language — the badge and the wording cannot drift apart.
 */
export function OrderStateBadge({ state }: { state: OrderState }) {
  const { t } = useI18n()

  return <span className={BADGES[state]}>{t(KEYS[state] as 'orders.state.draft')}</span>
}
