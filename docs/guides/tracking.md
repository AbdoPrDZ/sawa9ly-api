# Tracking product changes

A **tracker** is a subscription — "this user cares about this product" — not a
job. A separate queue decides what is actually worth fetching:

- a product **nobody tracks is never fetched**;
- a product is fetched **once per pass, however many people track it**, and every
  tracker on it is stamped afterwards. Ten users watching one product is one
  request, not ten.

```bash
python main.py catalogue save 5663 --user alice     # must be saved first
python main.py track watch 5663 --user alice
python main.py track list --user alice
python main.py track unwatch 5663 --user alice
```

When a watched product differs from what was stored, the row is updated, every
tracker on it gets `last_changed_at`, and the pass summary names the fields that
moved. Nothing records the old value — there is no change history.

## The queue

The queue is **global**: it follows every user's watches, so there is no user to
name and nothing to configure.

```bash
python main.py cron status                    # interval, delay, what is watched
python main.py cron run                        # one pass
python main.py cron listen                     # loop forever
```

A pass runs two jobs, and both are reported:

| Job | What it does |
| --- | --- |
| `tracking` | refreshes watched products, stamps the trackers that cared |
| `orders` | re-reads each posted order's own page and reconciles our state |

Each product is fetched using the first of the people watching it who has
sawa9ly credentials, so it is checked on behalf of someone who wanted it checked.
Clients are reused within a pass, so a hundred products watched by three people
costs at most three logins.

### The orders job

For every order that has an `origin_id` and is not already `done` or
`cancelled`, the pass reads the site's own page for it
(`src/services/order_page.py`) and moves our state to match. So an order you
cancelled on the site becomes `cancelled` here, and nobody has to retype it.

Two deliberate limits, both because `cancelled` is terminal and a wrong read
could not be undone by running the pass again:

- **Only `cancelled` is applied.** It is the one state the site has actually been
  seen to report. Any other wording is left alone and reported as a *disagreement*
  in the pass summary, rather than guessed at from a translation.
- **A refused move is reported, not forced.** If the site says `cancelled` but
  ours is `done`, the state machine forbids the move, so the summary says so and
  the order stays put.

An order with no `origin_id` is skipped — there is no page to read. That includes
any order placed before the id was recorded, which therefore needs the id filling
in by hand.

`cron status` shows `fetchable_targets` and an `unfetchable_targets` list, so a
queue that would do nothing is visible before you run it rather than from a pass
full of errors.

`cron run` is the one to point a scheduler at; the scheduler then owns the timing
and a crash cannot leave a loop behind:

```cron
*/5 * * * * cd /path/to/Sawa9ly-API && .venv/bin/python main.py cron run
```

`cron listen` owns the loop itself, for a machine with nothing else scheduling.
`--max-passes` stops after N passes, which is how it is tested.

| Variable | Default | Meaning |
| --- | --- | --- |
| `CRON_INTERVAL` | `300` | Seconds between passes |
| `CRON_DELAY` | `1.0` | Seconds between products inside a pass |

The delay matters: the queue hits the live site once per watched product, and
going slowly is what keeps it a guest rather than a load.

Two behaviours worth knowing:

- **A failing pass exits non-zero.** A scheduler only sees the exit code, so a
  misconfigured scanner would otherwise look healthy forever while the errors sat
  unread in a summary.
- **Only one pass runs at a time**, via a lock file in `data/`. A lock left by a
  hard kill is taken over after 15 minutes.

`/api/v1/trackers` mirrors the CLI over HTTP and accepts either an API key or a
dashboard token. There is deliberately no route that triggers a pass — one web
request fanning out into hundreds of requests to the site is the fastest way to
get blocked.
