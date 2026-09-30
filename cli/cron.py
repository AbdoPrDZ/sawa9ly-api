"""CLI: the scheduled queue."""

from src.config import Config
from src.services import CronError


class CronCli:
  """`cron` — run the tracking queue on an interval.

  The queue is global: it follows every user's watches and works out whose
  sawa9ly session to browse with, so there is nothing to name here. `run` is for
  an external scheduler (cron, Task Scheduler) and does one pass; `listen` owns
  the loop itself, for a machine with nothing else scheduling.
  """

  @staticmethod
  def register(commands):
    cron = commands.add_parser('cron', help="the scheduled tracking queue")
    actions = cron.add_subparsers(dest='action', required=True)

    run = actions.add_parser('run', help="one pass over everything watched")
    run.add_argument('--delay', type=float, default=None,
                     help=f"seconds between products (default {Config.CRON_DELAY_VAR})")

    listen = actions.add_parser('listen', help="run a pass every interval, forever")
    listen.add_argument('--interval', type=int, default=None,
                        help=f"seconds between passes (default {Config.CRON_INTERVAL_VAR})")
    listen.add_argument('--delay', type=float, default=None,
                        help="seconds between products")
    listen.add_argument('--max-passes', type=int, default=None,
                        help="stop after this many passes (for testing)")

    actions.add_parser('status', help="what the queue would do right now")

  @staticmethod
  def dispatch(args):
    from cli.base import Cli
    from src.services import Cron
    from src.utils.livewire import ensure_db

    # Before the first pass, not inside it. `Cron.run_once` and `Cron.listen` open
    # their own sessions and so never go through `Cli.db()`, which is what made
    # this work for every other command. Under Docker all three processes start
    # at once against one database, and nothing ordered the queue after the API -
    # so the queue asked for `trackers` and `orders` a moment before the API's
    # `create_all` had made them, and reported a missing relation rather than the
    # thing that was actually true. A queue that depends on the API having booted
    # first is a queue that fails whenever it is started on its own.
    ensure_db()

    if args.action == 'run':
      summary = Cron.run_once(delay=args.delay)
      # A scheduled job is judged by its exit code, so a pass that hit problems
      # must not report success. Without this a misconfigured scanner looks
      # healthy forever, because the errors are only in the summary nobody reads.
      CronCli._fail_on_errors(summary)

      return summary

    if args.action == 'listen':
      results = Cron.listen(
        interval=args.interval,
        delay=args.delay,
        max_passes=args.max_passes,
      )
      failed = [r for r in results if CronCli._errors_of(r)]
      CronCli._fail_on_errors({'errors': [e for r in failed for e in CronCli._errors_of(r)]})

      # The human-readable progress is on stderr; stdout is the summaries, so
      # this can be piped or captured.
      return {'passes': len(results), 'failed_passes': len(failed), 'runs': results}

    if args.action == 'status':
      with Cli.db() as db:
        return Cron.status(db)

  @staticmethod
  def _errors_of(summary):
    """Every error in a pass summary, including the ones a job reported."""
    job_errors = []

    for result in (summary.get('jobs') or {}).values():
      job_errors.extend(result.get('errors') or [])

    return list(summary.get('errors') or []) + job_errors

  @staticmethod
  def _fail_on_errors(summary):
    errors = CronCli._errors_of(summary)

    if not errors:
      return

    shown = '; '.join(errors[:3])
    more = f" (and {len(errors) - 3} more)" if len(errors) > 3 else ""

    raise CronError(f"{len(errors)} problem(s) during the pass: {shown}{more}")
