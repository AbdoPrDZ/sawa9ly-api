"""Watching products for changes.

This service knows about products and about comparing two scrapes. It knows
nothing about *when* to run: that is `src/services/cron.py`, which calls
`Tracking.scan_once` on an interval.

Two rules shape everything here:

- **A product nobody tracks is never fetched.** The queue works from the distinct
  set of watched targets, so an untracked product costs nothing and the site is
  not touched on its account.
- **A product is fetched once per pass, however many people track it.** The
  distinct set is collapsed first, and every tracker on that target is stamped
  afterwards. Ten users watching one product is one request, not ten.
"""

import time
from datetime import timedelta

from src.db import session_scope, utcnow
from src.models import Product, TargetModel, Tracker, User
from src.services import Product as ProductPage
from src.utils import Livewire
from src.utils.livewire import LivewireError

# The stored fields a scan compares. Anything not listed is not diffed, so
# adding a column to Product does not silently start generating change records.
TRACKED_FIELDS = (
  'title',
  'price',
  'available',
  'description',
  'images',
  'figures',
  'categories',
)

# Stored field -> the key that carries it in a `get_info()` result.
#
# This mapping is explicit because they are not all the same name: the scrape
# reports `availability` and the column is `available`. Reading the wrong key
# yields None, which looks like a change on every single pass and floods the log.
SCRAPE_KEYS = {
  'title': 'title',
  'price': 'price',
  'available': 'availability',
  'description': 'description',
  'images': 'images',
  'figures': 'figures',
  'categories': 'categories',
}

# Products missing from the catalogue cannot be tracked, so this is what a
# tracker for a stranger's product id would resolve to.
UNKNOWN_TARGET = "Product {product_id} is not in the catalogue; save it first."


class TrackingError(Exception):
  """A tracking request cannot be carried out."""


class Tracking:
  """Subscriptions to watched entities, and the scan that refreshes them."""

  # --- subscriptions --------------------------------------------------

  @staticmethod
  def watch_product(db, product_id, username):
    """Start watching a saved product for a user.

    Raises:
        TrackingError: If the product is not in the catalogue, or the target
          name is not one the queue knows how to refresh.
    """
    user = Tracking._user(db, username)
    product = Product.get(db, product_id)

    if product is None:
      raise TrackingError(UNKNOWN_TARGET.format(product_id=product_id))

    tracker, created = Tracker.watch(
      db, user.id, TargetModel.PRODUCT, product.id
    )

    return tracker, created

  @staticmethod
  def unwatch_product(db, product_id, username):
    """Stop watching. True if this user was watching it."""
    user = Tracking._user(db, username)
    product = Product.get(db, product_id)

    if product is None:
      return False

    return Tracker.unwatch(db, user.id, TargetModel.PRODUCT, product.id)

  @staticmethod
  def for_user(db, username, target_model=None):
    """A user's trackers, with each target resolved for display."""
    user = Tracking._user(db, username)

    return [
      Tracking.describe(db, tracker)
      for tracker in Tracker.for_user(db, user.id, target_model)
    ]

  @staticmethod
  def describe(db, tracker):
    """One tracker as a dict, with the watched product attached.

    Kept here so the CLI and the API render a tracker the same way, rather than
    each resolving the target itself.
    """
    row = tracker.as_dict()
    product = Product.get_by_id(db, tracker.target_id)
    row['target'] = product.as_dict() if product else None

    return row

  @staticmethod
  def watched_count(db):
    """How many distinct targets are being watched, and by how many trackers."""
    targets = Tracker.watched_targets(db)

    return {
      'targets': len(targets),
      'trackers': sum(
        len(Tracker.trackers_for(db, t['target_model'], t['target_id']))
        for t in targets
      ),
    }

  @staticmethod
  def scanner_report(db):
    """Which watchers could actually fetch, and which targets nobody can.

    Lets an operator see a queue that will do nothing *before* running it, rather
    than discovering it from a pass full of errors.
    """
    targets = Tracker.watched_targets(db)
    fetchable = 0
    blocked = []

    for target in targets:
      trackers = Tracker.trackers_for(db, target['target_model'], target['target_id'])
      watchers = [
        user for user in (User.get_by_id(db, t.user_id) for t in trackers)
        if user is not None
      ]
      usable = [
        user for user in watchers
        if user.sawa9ly_email and user.sawa9ly_password
      ]

      if usable:
        fetchable += 1
      else:
        blocked.append({
          'target_model': target['target_model'],
          'target_id': target['target_id'],
          'watched_by': [user.username for user in watchers],
        })

    return {'fetchable': fetchable, 'unfetchable': blocked}

  # --- the scan -------------------------------------------------------

  @staticmethod
  def scan_once(delay=None, target_model=None, now=None):
    """Refresh every watched target once, across every user.

    There is no scanner to name. Each product is fetched on behalf of the people
    watching it, using the first of them who actually has sawa9ly credentials —
    so the queue is global and needs no configuration, and the session used is
    one belonging to somebody who wanted the product checked.

    Clients are built lazily and reused within the pass, so a hundred products
    watched by three people costs at most three logins.

    Returns a summary dict rather than raising on a single bad target — one
    unreachable product must not stop the rest of the pass, and the error is
    reported in `errors` so the operator can see it.
    """
    from src.config import Config

    delay = Config.cron_delay() if delay is None else delay
    checked = now or utcnow()

    summary = {
      'scanned': 0,
      'changed': 0,
      'skipped': 0,
      'trackers': 0,
      'scanners': 0,
      'changed_fields': {},
      'errors': [],
    }

    with session_scope() as db:
      targets = Tracker.watched_targets(db, target_model)
      clients = {}

      for target in targets:
        product = Product.get_by_id(db, target['target_id'])

        if product is None:
          # A tracker whose target row has gone should not happen, because the
          # foreign key cascades. Reported rather than silently dropped.
          summary['skipped'] += 1
          continue

        scanner = Tracking._scanner_for(db, target, clients)

        if scanner is None:
          summary['scanned'] += 1
          summary['errors'].append(
            f"{TargetModel.PRODUCT} {product.product_id}: none of the users "
            "watching it have sawa9ly credentials, so it cannot be fetched. "
            "Record them with: python main.py user add <username> --email ... "
            "--password ..."
          )
          continue

        if delay and summary['scanned']:
          time.sleep(delay)

        summary['scanned'] += 1

        try:
          info = ProductPage(product.product_id, scanner).get_info()
        except Exception as error:  # noqa: BLE001 - one bad page must not stop the pass
          summary['errors'].append(
            f"{TargetModel.PRODUCT} {product.product_id}: {error}"
          )
          continue

        found = Tracking._apply(db, product, info, checked)
        summary['trackers'] += found['trackers']

        if found['changed_fields']:
          summary['changed'] += 1
          summary['changed_fields'][str(product.product_id)] = found['changed_fields']

      summary['scanners'] = len(clients)

    return summary

  @staticmethod
  def _scanner_for(db, target, clients):
    """A usable Livewire client for a target, from the people watching it.

    Returns the cached client when this user has been used already in the pass.
    Returns None when nobody watching the product can actually reach the site,
    which the caller reports rather than falling back to some unrelated account.
    """
    for tracker in Tracker.trackers_for(db, target['target_model'], target['target_id']):
      if tracker.user_id in clients:
        return clients[tracker.user_id]

      user = User.get_by_id(db, tracker.user_id)

      if user is None or not (user.sawa9ly_email and user.sawa9ly_password):
        continue

      try:
        clients[tracker.user_id] = Livewire(user.username)
      except LivewireError:
        # The stored credentials were rejected. Try the next watcher rather than
        # failing the pass, and let the error surface on the fetch if it recurs.
        continue

      return clients[tracker.user_id]

    return None

  @staticmethod
  def _apply(db, product, info, checked):
    """Diff a scrape against the stored row, update it, and stamp the trackers.

    The diff is transient: it decides whether `last_changed_at` moves and which
    field names the pass reports. Nothing is stored, so the only record of a
    change is the updated product and that timestamp on the trackers.

    Returns the changed field names and how many trackers were stamped, so the
    caller can count without re-querying.
    """
    previous = product.as_dict()
    changed_fields = []

    for field in TRACKED_FIELDS:
      if not _same(previous.get(field), info.get(SCRAPE_KEYS[field])):
        changed_fields.append(field)

    # Save writes every tracked field, so the stored row cannot disagree with
    # what the site currently says.
    Product.save(db, product.product_id, info)

    trackers = Tracker.trackers_for(db, TargetModel.PRODUCT, product.id)
    changed = bool(changed_fields)

    for tracker in trackers:
      tracker.last_checked_at = checked

      if changed:
        tracker.last_changed_at = checked

    db.commit()

    return {'changed_fields': changed_fields, 'trackers': len(trackers)}

  # --- helpers --------------------------------------------------------

  @staticmethod
  def _user(db, username):
    from src.models import User

    user = User.get(db, username)

    if user is None:
      raise TrackingError(
        f"No user named '{username}'. Create it with: "
        f"python main.py user add {username}"
      )

    return user

  @staticmethod
  def due_cutoff(interval, now=None):
    """The timestamp a tracker must predate to be due for another pass."""
    return (now or utcnow()) - timedelta(seconds=interval)


def _same(old, new):
    """Whether a field is unchanged, comparing lists as lists.

    `as_dict` decodes the JSON columns, so an unchanged image list comes back as
    a list on both sides and compares equal — without this, every pass would
    report every list as changed.
    """
    if isinstance(old, list) or isinstance(new, list):
        return (old or []) == (new or [])

    return old == new

