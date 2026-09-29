# Tracking and the Cron Queue

Watching products for changes, and the queue that checks them.

## What tracking is

A **tracker** is a subscription: "this user cares about this product". It is not
a job. The queue decides what is worth fetching, and collapses subscriptions
into work.

Two rules shape everything:

- **A product nobody tracks is never fetched.** The queue works from the set of
  watched targets, so an untracked product costs nothing and the site is not
  touched on its account.
- **A product is fetched once per pass, however many people track it.** Ten users
  watching one product is one request, not ten. Every tracker on that target is
  stamped afterwards.

`Tracker` is deliberately generic — `target_model` names the entity and
`target_id` is that entity's own primary key. For a product that is the internal
`products.id`, not the sawa9ly id, so deleting a catalogue row cascades the
subscriptions away instead of leaving them pointing at nothing. The unique
constraint is per (target, **user**), not per target, precisely so several users
can watch the same thing.

## What a pass records, and what it does not

A pass compares the scrape against the stored row, writes the new values, and
stamps `last_checked_at` on every tracker for that product — plus
`last_changed_at` if anything differed.

**There is no change history.** Nothing records the old value. The only trace of
a change is the updated product and that timestamp, and a pass summary naming the
fields that moved:

```json
"changed_fields": { "5663": ["price", "available"] }
```

That was a deliberate omission, not an oversight. If a history is wanted later,
it is a new table to ask for — not something to add on the way to the queue.

The field list and an explicit map from stored field to the key a scrape uses
both live in `src/services/tracking.py`. They are not all the same name — the
scrape reports `availability`, the column is `available` — and reading the wrong
key returns `None`, which looks like a change on every single pass. That bug
happened; the map is the fix.

## Scheduled work, by kind

| Service | Knows about |
| --- | --- |
| `src/services/tracking.py` | products, comparing two scrapes, what to record |
| `src/services/order_sync.py` | posted orders, reconciling our state with the site's |
| `src/services/cron.py` | timing, locking, reporting. Nothing about what it runs |

`Cron` calls `scan_once` on each through a small job registry, so adding a third
kind of scheduled work means adding a job, not teaching the scheduler about it. A
job is a `(name, callable)` pair and is handed `delay` and `target_model` whether
or not it uses them, because `run_once` passes the same keywords to every one.

`OrderSync.scan_once` is the second job. It reads each order's own page through
`src/services/order_page.py` and moves our state to the site's — but only for
`cancelled`, the one site state actually observed. Anything else is reported as a
**disagreement** and left alone: `cancelled` is terminal, so a state guessed from
an unrecognised word could not be undone by running the pass again. A `done` or
`cancelled` order is skipped entirely rather than re-read.

Orders without an `origin_id` are skipped: there is no page to read. An order
placed before the id was recorded is therefore never reconciled, and its id has
to be set by hand.

## Running it

The queue is **global**. There is no user to name: it follows every user's
watches and decides for itself whose session to browse with.

```bash
python main.py track watch 5663 --user alice   # subscribe
python main.py track list --user alice
python main.py track unwatch 5663 --user alice
python main.py cron status                     # what it would do
python main.py cron run                        # one pass
python main.py cron listen                     # loop forever
```

`--user` belongs to `track`, because subscribing is somebody's decision. It does
not belong to `cron`: scheduling is nobody's decision.

**Which session fetches a product.** The first of the people watching it who
actually has sawa9ly credentials. So a product is checked on behalf of someone who
wanted it checked, clients are built lazily and reused within the pass, and a
hundred products watched by three people costs at most three logins. When nobody
watching a product can reach the site, that target is reported as an error naming
the accounts involved, and the rest of the pass continues.

`cron status` reports the same thing *before* a run: `fetchable_targets` and an
`unfetchable_targets` list, so a queue that would do nothing is visible without
running it and reading the errors.

- **`cron run`** is one pass, and is what an OS scheduler should call. The
  scheduler then owns the timing and a crash cannot leave a loop behind.
- **`cron listen`** owns the loop, for a machine with nothing else scheduling.
  `--max-passes` stops after a number of passes, which is how it is tested.


## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `CRON_INTERVAL` | `300` | Seconds between passes |
| `CRON_DELAY` | `1.0` | Seconds between products inside a pass |

The delay matters: the queue hits the live site once per watched product, and
going slowly is what keeps it a guest rather than a load.

## Two things that will bite

- **A failing pass exits non-zero.** `cron run` raises when a pass reported any
  error. Without that a misconfigured scanner looks healthy forever, because the
  errors are only in a summary nobody reads. The exit code is all cron sees.
- **Only one pass runs at a time.** `Cron.listen` takes `data/cron.lock`
  exclusively, so two scheduler entries firing together cannot double-scrape. A
  lock older than 15 minutes is taken over, because the alternative is a queue
  that never runs again after one hard kill.

An empty queue builds no client and needs no credentials, so `cron run` before
anything is watched is a clean no-op rather than a failed login.

## API

`/api/v1/trackers` mirrors the CLI: list, watch, unwatch. It accepts **either** an API
key or a dashboard token, because both a machine and the browser need to manage
the same subscriptions.

There is deliberately **no route that triggers a pass**: one web request fanning
out into hundreds of requests to the live site is the fastest way to get blocked.
Scheduling belongs to `python main.py cron`.
