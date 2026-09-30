# Docker

One image, `sawa9ly-api:latest`, built by the `Dockerfile`: the dashboard is
compiled in a Node stage, and the runtime stage is Python and nothing else. Two
stacks, which differ only in where the database lives.

```bash
cp .env.docker.example .env.docker     # then set SUPER_ADMIN_PASSWORD
docker compose --env-file .env.docker -f docker-compose.sqlite.yml up -d --build
```

or, for a deployment that is not a single machine:

```bash
cp .env.docker.example .env.docker     # then set both passwords
docker compose --env-file .env.docker -f docker-compose.postgres.yml up -d --build
```

**`--env-file .env.docker` is required, and the reason is worth knowing.** A
service's `env_file:` puts variables *into a container*; the `${...}` in a compose
file reads them *from the shell, or from the file named by `--env-file`*. The two
never overlap, so without the flag a value in `.env.docker` is invisible to the
interpolation — and the error says the variable is *missing* rather than merely
unread, which points you at the compose file instead of at your env file. Every
command in this section includes the flag for that reason.

The sqlite stack sets `DB_DRIVER=sqlite` and blanks every server-side database
variable. That is deliberate: one shared `.env.docker` is going to carry `DB_NAME`
and `DB_PASSWORD` because the postgres stack needs them, and the application
prefers a server over a file the moment `DB_NAME` is set. Without the blanking,
the sqlite stack would boot, choose a database, and spend its life failing to
reach a postgres it does not have.

| | `docker-compose.sqlite.yml` | `docker-compose.postgres.yml` |
| --- | --- | --- |
| Database | `sawa9ly.db` on a volume | a `postgres:17-alpine` container |
| Persistent volume | `sawa9ly-database` | `sawa9ly-postgres` |
| Use it for | one machine, trying it out | anything you care about |

Each stack runs three containers from the one image — `serve`, `telegram` and
`cron` — differing only in their command. They are separate because they fail
separately and are restarted separately: a queue that wedges should not take the
dashboard down with it. The port is published on the host's loopback only,
because this is an admin surface with real API keys behind it.

**Talking to a running container.** The CLI is installed in the image as
`sawa9ly-api`, so a running container can be asked questions without a shell in it:

```bash
docker exec <container> sawa9ly-api user list
docker exec <container> sawa9ly-api product show 5663
docker exec <container> sawa9ly-api cron run
```

Or, with compose, by service name:

```bash
docker compose -f docker-compose.sqlite.yml exec serve sawa9ly-api user list
```

The exit code is the CLI's own — `cron run` reports a failed pass through it, so a
scheduler sees a broken queue rather than a healthy-looking one. Any of the three
containers will do; they share the same database and the same code. Running it in
the `cron` container respects that container's own queue lock, so a manual pass
refuses while a pass is already running rather than doubling up.

**Inside the container** the directories move to where a Linux system keeps such
things, and the image sets that itself:

| | Local | Container |
| --- | --- | --- |
| Database | `database/sawa9ly.db` | `/var/lib/sawa9ly` |
| Logs | `logs/sawa9ly-*.log` | `/var/log/sawa9ly` |
| Lock files | `data/*.lock` | `/tmp/sawa9ly` |

The lock files move to `/tmp` because a lock only means anything while the process
holding it is alive, and a container's writable layer is thrown away with the
container. Putting them on a volume would be the opposite of the point.

The logs are **not** on a volume. Each container already has its own
`docker logs`, which is one stream per process and carries the same lines, so
persisting the files as well would mean a second copy to rotate and delete with
nothing in it the streams do not already have.

Two things worth knowing before using SQLite in containers: it is three writers on
one file, which is fine on Linux with a local volume but the part of this setup
most likely to be slow or to lock on Docker Desktop under macOS and Windows — and
the schema is applied with `create_all`, which does not migrate an existing file.

The database connection for the postgres stack is passed as the discrete `DB_*`
variables — `DB_NAME`, `DB_USER`, `DB_PASSWORD` — rather than one `DATABASE_URL`,
on purpose: the application url-quotes a password assembled from those parts, and
takes a `DATABASE_URL` verbatim, so a password containing `@`, `/` or `:` works
under the first and silently connects to the wrong host under the second.

`DB_PASSWORD` is the only database password you write. The postgres image insists
on the name `POSTGRES_PASSWORD`, and the compose file translates one into the
other, so the value exists once rather than twice.

`.dockerignore` excludes `.env`, so no password, API key or bot token is ever
baked into a layer, and excludes `database/`, `data/` and `logs/`, so one
environment's accounts cannot travel into another's deployment.
