"""The scheduled queue: runs jobs on an interval, one at a time.

This service is deliberately ignorant of what the jobs do. It knows about
timing, about not running two passes at once, and about reporting what happened.
The product-refreshing logic lives in `src/services/tracking.py`; this file
calls it.

Two ways to run it:

- `python main.py cron run` — a single pass. This is what an OS scheduler
  (cron, Task Scheduler, a container's own scheduler) should call, because the
  scheduler then owns the timing and a crash cannot leave a loop behind.
- `python main.py cron listen` — a loop, for a machine where nothing else
  schedules anything.

Only one pass may run at a time. A lock file makes that true across processes,
so two cron entries firing together cannot double-scrape the site.
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config import Config

logger = logging.getLogger(__name__)

# The lock lives beside the database so a relative path cannot put it somewhere
# that is not shared between processes.
LOCK_NAME = "cron.lock"

# Refuse rather than wait: a pass that is still running means the previous one
# is slow, and blocking here would just queue passes up behind each other.
LOCK_STALE_SECONDS = 900


class CronError(Exception):
  """The queue cannot start or continue."""


class Cron:
  """Runs the registered jobs on a fixed interval."""

  @staticmethod
  def jobs():
    """The (name, callable) pairs a pass runs, in order.

    Imported here rather than at module level so a job's own dependencies are
    only loaded when the queue is actually used — the CLI does not need pyquery
    and the site client to manage a tracker.

    A job takes no scanner argument. The queue is global: it works across every
    user's watches and decides for itself whose session to browse with.
    """
    from src.services.order_sync import OrderSync
    from src.services.tracking import Tracking

    return (
      ('tracking', Tracking.scan_once),
      ('orders', OrderSync.scan_once),
    )

  # --- one pass -------------------------------------------------------

  @staticmethod
  def run_once(**job_kwargs):
    """Run every job once and collect what they report.

    A job that raises is recorded and the rest still run: one broken job must
    not stop the others, and the summary has to say which one failed.
    """
    started = datetime.now(timezone.utc)
    summary = {
      'started_at': str(started),
      'finished_at': None,
      'duration_seconds': 0.0,
      'jobs': {},
      'errors': [],
    }

    for name, job in Cron.jobs():
      try:
        summary['jobs'][name] = job(**job_kwargs)
      except Exception as error:  # noqa: BLE001 - a job must not stop the queue
        summary['errors'].append(f"{name}: {error}")

    finished = datetime.now(timezone.utc)
    summary['finished_at'] = str(finished)
    summary['duration_seconds'] = round((finished - started).total_seconds(), 3)

    return summary

  # --- listening ------------------------------------------------------

  @staticmethod
  def listen(interval=None, delay=None, once=False, target_model=None,
             max_passes=None):
    """Run a pass every `interval` seconds until interrupted.

    `max_passes` stops after a number of passes, which is what makes this
    testable without Ctrl-C. `once` is the same as a single `run_once`.
    """
    interval = Config.cron_interval() if interval is None else interval

    if interval < 1:
      raise CronError(f"The interval must be at least 1 second, got {interval}.")

    job_kwargs = {'delay': delay, 'target_model': target_model}
    passes = 0
    results = []

    with Cron._lock():
      while True:
        summary = Cron.run_once(**job_kwargs)
        passes += 1
        results.append(summary)
        Cron._report(summary, passes, interval)

        if once or (max_passes is not None and passes >= max_passes):
          return results

        try:
          time.sleep(interval)
        except KeyboardInterrupt:
          Cron._say("\nstopped after {0} pass(es)".format(passes))
          return results

  @staticmethod
  def status(db):
    """What the queue is configured to do, and what it is watching.

    `unfetchable` is the useful part: those targets are watched but nobody
    watching them can reach the site, so a pass will report them as errors. Seeing
    that here beats reading it out of a failed run.
    """
    from src.services.tracking import Tracking

    watched = Tracking.watched_count(db)
    report = Tracking.scanner_report(db)

    return {
      'interval_seconds': Config.cron_interval(),
      'delay_seconds': Config.cron_delay(),
      'watched_targets': watched['targets'],
      'trackers': watched['trackers'],
      'fetchable_targets': report['fetchable'],
      'unfetchable_targets': report['unfetchable'],
      'jobs': [name for name, _ in Cron.jobs()],
    }

  # --- the lock -------------------------------------------------------

  @staticmethod
  def _lock_path():
    return Path(Config.DATA_DIR) / LOCK_NAME

  class _Lock:
    """A lock file, held for the duration of a `with` block.

    Created exclusively so the OS decides who wins, rather than a check-then-write
    that two processes can both pass. A lock older than `stale_seconds` is taken
    over, because the alternative is a queue that never runs again after one hard
    kill.

    Parameterised rather than hardcoded to the cron file so the Telegram listener
    can use the same mechanism for the same reason — one process per something
    that cannot have two — without a second copy of it. `stale_seconds` of 0
    never takes over, which is right for a process someone started by hand.
    """

    def __init__(self, path, stale_seconds, message):
      self.path = path
      self.stale_seconds = stale_seconds
      self.message = message
      self.held = False

    def __enter__(self):
      self.path.parent.mkdir(parents=True, exist_ok=True)

      for attempt in (1, 2):
        try:
          handle = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
          if attempt == 1 and self._take_over_if_stale():
            continue

          raise CronError(self.message.format(path=self.path))

        with os.fdopen(handle, "w") as stream:
          stream.write(f"{os.getpid()} {datetime.now(timezone.utc).isoformat()}")

        self.held = True

        return self

    def __exit__(self, *_):
      if self.held:
        try:
          self.path.unlink()
        except FileNotFoundError:
          pass

        self.held = False

      return False

    def _take_over_if_stale(self):
      """Whether to remove this lock and try again.

      `stale_seconds` of 0 means **never** take over. That has to be said
      explicitly rather than left to the comparison below: a lock written a
      moment ago is already a fraction of a second old, so `age <= 0` is false
      and the naive reading of it is "take over immediately" — which is the
      exact opposite of what a caller asking for 0 wants.
      """
      if self.stale_seconds <= 0:
        return False

      try:
        age = time.time() - self.path.stat().st_mtime
      except FileNotFoundError:
        return True

      if age <= self.stale_seconds:
        return False

      Cron._say(f"removing a stale lock from {int(age)}s ago")
      try:
        self.path.unlink()
      except FileNotFoundError:
        pass

      return True

  @staticmethod
  def _lock():
    return Cron._Lock(
      Cron._lock_path(),
      LOCK_STALE_SECONDS,
      "Another pass is already running (lock: {path}). "
      "If you are sure nothing is, delete that file.",
    )

  # --- output ---------------------------------------------------------

  @staticmethod
  def _report(summary, passes, interval):
    """One line per job, then anything any of them complained about.

    Reports whatever jobs the queue is running rather than the one it was written
    for, so a job added later cannot pass by every time without being mentioned.
    """
    Cron._say(
      "pass {0} in {1}s (every {2}s)".format(
        passes, summary['duration_seconds'], interval
      )
    )

    for name, result in summary['jobs'].items():
      Cron._say(f"  {name}: {Cron._counts(result)}")

    for message in summary['errors']:
      Cron._say(f"  ! {message}")

    for name, result in summary['jobs'].items():
      for message in result.get('errors', []):
        Cron._say(f"  ! {name}: {message}")

      for message in result.get('disagreements', []):
        # Not a failure: the site says something we did not act on, which is
        # worth reading but is not a broken pass.
        Cron._say(f"  ~ {name}: {message}")

      # Notification failures are reported and deliberately kept out of `errors`,
      # so `cron run` does not exit non-zero because one person muted a bot. The
      # scan did its job; the message did not go out.
      for message in result.get('notify_errors', []):
        Cron._say(f"  ~ {name}: could not notify - {message}")

  @staticmethod
  def _counts(result):
    """A job's headline numbers, leaving out the ones it has nothing in.

    Not every job has every figure, so a fixed list is filtered rather than
    printed with zeros: a queue that did nothing should read as "nothing to do",
    not as a page of zeroes.
    """
    if not isinstance(result, dict):
      return str(result)

    parts = [f"scanned {result['scanned']}"] if 'scanned' in result else []

    parts += [
      f"{key} {result[key]}"
      for key in ('changed', 'unchanged', 'skipped', 'notified', 'trackers', 'clients')
      if result.get(key)
    ]

    return ", ".join(parts) or "nothing to do"

  @staticmethod
  def _say(message):
    """Progress goes to stderr, and to the queue's own log.

    stderr on its own is not a record. A queue is run in the background and then
    never watched again, so the only evidence it did anything is what it wrote to
    a file — and a pass that failed silently looks exactly like a pass that found
    nothing to do. Both destinations, because they are read by different people:
    one watching the terminal, one reading the log after the fact.
    """
    print(f"cron: {message}", file=sys.stderr, flush=True)
    logger.info("%s", message)
