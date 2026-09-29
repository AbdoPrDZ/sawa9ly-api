"""Reconciling posted orders against the site's own view of them.

`Tracking` is the same idea for products: something is watched, and a pass brings
what we stored back in line with what the site currently says. Here the thing
watched is an order that has been posted, and what can change is its state.

This service knows nothing about *when* to run: that is `src/services/cron.py`,
which calls `OrderSync.scan_once` on an interval.

Two rules shape everything here:

- **Only an order the site gave a number for is ever fetched.** An order without
  `origin_id` has no page to read, so a draft costs nothing and the site is not
  touched on its account.
- **Only a state the site has actually been seen to report is applied.** Anything
  else is reported as a disagreement and left alone. Overwriting our state from
  an unrecognised word would move an order on the strength of a translation
  mistake, and there is no way back out of `cancelled` — so a wrong read here
  cannot be undone by running the pass again.
"""

import logging
import time

from src.db import session_scope
from src.models import Order, OrderState, User
from src.services.order_page import OrderPage
from src.utils import Livewire
from src.utils.livewire import LivewireError

logger = logging.getLogger(__name__)

#: The states whose order the site could still move on from. A done or cancelled
#: order has run its course, so re-reading it costs a request and can only report
#: the answer already stored.
OPEN_STATES = (OrderState.DRAFT, OrderState.CONFIRMED)


class OrderSync:
  """Refreshes the state of posted orders from the site."""

  @staticmethod
  def scan_once(delay=None, target_model=None):
    """Reconcile every posted order once, across every user.

    `target_model` is accepted and ignored: the queue hands every job the same
    keyword arguments, and filtering products is not something an order pass can
    do.

    Clients are built lazily and reused within the pass, so a hundred orders
    across three users costs at most three logins.

    Returns a summary dict rather than raising on a single bad order — one
    unreachable order must not stop the rest of the pass, and the error is reported
    in `errors` so the operator can see it.
    """
    from src.config import Config

    delay = Config.cron_delay() if delay is None else delay

    summary = {
      'scanned': 0,
      'changed': 0,
      'unchanged': 0,
      'skipped': 0,
      'clients': 0,
      'disagreements': [],
      'errors': [],
    }

    with session_scope() as db:
      clients = {}
      fetched = 0

      for order in Order.all(db):
        if order.origin_id is None:
          # No page to read. A draft, or an order posted before the id was kept.
          summary['skipped'] += 1
          continue

        if order.state not in OPEN_STATES:
          summary['skipped'] += 1
          continue

        client = OrderSync._client_for(db, order, clients)

        if client is None:
          summary['skipped'] += 1
          summary['errors'].append(
            f"order {order.id} (site {order.origin_id}): its owner cannot reach the "
            "site. Record their sawa9ly credentials with: python main.py user "
            "add <username> --email ... --password ..."
          )
          continue

        if delay and fetched:
          time.sleep(delay)

        fetched += 1
        summary['scanned'] += 1

        try:
          info = OrderPage(order.origin_id, client).get_info()
        except Exception as error:  # noqa: BLE001 - one bad page must not stop the pass
          summary['errors'].append(f"order {order.id} (site {order.origin_id}): {error}")
          continue

        OrderSync._apply(db, order, info, summary)

      summary['clients'] = len(clients)

    return summary

  # --- applying a result ----------------------------------------------

  @staticmethod
  def _apply(db, order, info, summary):
    """Move the order to the state the site reports, when that is safe to do.

    A disagreement is recorded rather than resolved whenever the site's state
    cannot be applied — because the site's wording is not one we recognise, or
    because our state machine forbids the move. Both are cases where guessing
    would be worse than saying so.
    """
    state = info.get('status')
    raw = info.get('raw_status')

    if state is None:
      summary['disagreements'].append(
        f"order {order.id} (site {order.origin_id}): the site reports "
        f"{raw!r}, which is not a state this API knows; ours is still "
        f"{order.state!r} and was left alone"
      )
      return

    if state == order.state:
      summary['unchanged'] += 1
      return

    if not OrderState.can_transition(order.state, state):
      allowed = ", ".join(OrderState.TRANSITIONS.get(order.state, ())) or "nothing"

      summary['disagreements'].append(
        f"order {order.id} (site {order.origin_id}): the site says {state!r} but "
        f"ours is {order.state!r}, and {order.state!r} cannot become {state!r} "
        f"(allowed: {allowed}). Move it by hand if the site is right"
      )
      return

    previous = order.state
    order.transition(db, state)
    summary['changed'] += 1

    logger.info(
      "order %s: %s -> %s (site %s)", order.id, previous, state, order.origin_id
    )

  # --- helpers --------------------------------------------------------

  @staticmethod
  def _client_for(db, order, clients):
    """A Livewire client for the user who placed this order.

    The order page is inside that user's account, so unlike a product — which any
    watcher may fetch — there is no second choice about whose session reads it.

    Returns the cached client when this user has been used already in the pass,
    and None when they have no usable credentials, which the caller reports rather
    than falling back to some unrelated account.
    """
    user = User.get_by_id(db, order.user_id)

    if user is None:
      return None

    if user.id in clients:
      return clients[user.id]

    if not (user.sawa9ly_email and user.sawa9ly_password):
      return None

    try:
      clients[user.id] = Livewire(user.username)
    except LivewireError:
      # The stored credentials were rejected. Let it surface on the fetch.
      return None

    return clients[user.id]
