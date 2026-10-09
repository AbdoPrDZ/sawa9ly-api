"""A sliding-window rate limit, for the public order form.

The storefront's order route is reachable by anyone, and an order placed there is
real and cannot be cancelled. There is no captcha in this project, so the brake is
a simple one: count the hits on a key and refuse once the key has spent its
allowance inside the window.

It is in-memory and per-process, which is the whole picture because `serve` is a
single uvicorn process. A restart forgets every count, and that is acceptable for
a spam brake rather than a security control. It is not a substitute for the
honeypot or for thinking about what a public order endpoint means.
"""

import threading
import time

#: Above this many distinct keys, the table is pruned of windows that have
#: elapsed. Without it a flood of one-off keys would grow the dict without bound.
PRUNE_AT = 10000


class Throttle:
  """Allow at most `limit` hits per key per `window` seconds."""

  def __init__(self, limit, window):
    self.limit = limit
    self.window = window
    self._hits: dict = {}
    self._lock = threading.Lock()

  def allow(self, key, now=None):
    """Record a hit for `key`, returning False when it is over its allowance."""
    now = time.monotonic() if now is None else now
    cutoff = now - self.window

    with self._lock:
      if len(self._hits) > PRUNE_AT:
        self._prune(cutoff)

      hits = [stamp for stamp in self._hits.get(key, ()) if stamp > cutoff]

      if len(hits) >= self.limit:
        self._hits[key] = hits
        return False

      hits.append(now)
      self._hits[key] = hits

      return True

  def _prune(self, cutoff):
    """Drop every key whose window has fully elapsed. Called under the lock."""
    self._hits = {
      key: hits for key, hits in self._hits.items()
      if any(stamp > cutoff for stamp in hits)
    }
