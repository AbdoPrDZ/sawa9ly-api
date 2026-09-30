# Logging

**Logging** — on by default, one file per subsystem under `logs/`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | — | One file receiving everything, instead of the five |
| `LOG_FORMAT` | `text` | `json` for one object per line |

The five files, and what lands in each:

| File | Holds |
| --- | --- |
| `sawa9ly-api.log` | the API, the site scraper, and the HTTP access log |
| `sawa9ly-dashboard.log` | browser requests for the dashboard and published pages |
| `sawa9ly-cli.log` | which command ran, for which account, and whether it worked |
| `sawa9ly-cron.log` | the queue: tracking, order sync, notifications |
| `sawa9ly-telegram.log` | the bot |

A file appears the first time something is written to it, so a quiet day leaves
none behind. Everything also goes to the console, as before.

`INFO` rather than `WARNING` is the default because the queue and the bot run in
the background: their pass summaries are the only record that they ran at all. The
HTTP access log stays at `INFO` whatever `LOG_LEVEL` is set to — it is the api
log's reason for existing, and turning the level up to quiet the rest should not
delete the traffic history too.

Any log line mentioning a password, token, key or cookie has the value replaced
with `[redacted]`, whether the value was passed as an argument or already built
into the string.
