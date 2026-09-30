# syntax=docker/dockerfile:1

# =============================================================================
# The dashboard.
#
# Built here rather than on the host, so the image never depends on whether
# someone remembered to run `npm run build` first, and so the bundle it serves is
# built from the source sitting next to it. Installed from the lockfile with
# `npm ci`, so the result is the same build every time rather than whatever npm
# resolved on the day.
# =============================================================================
FROM node:22-alpine AS dashboard

WORKDIR /build

# The manifests alone first. This layer is only rebuilt when they change, so
# editing a component does not reinstall the whole tree.
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY dashboard/ ./
RUN npm run build


# =============================================================================
# The application.
# =============================================================================
FROM python:3.14-slim AS app

# Unbuffered, or nothing appears in `docker logs` until the process exits - and
# for a service designed to run forever, that is never.
#
# The three writable locations, and why they are where they are. A Linux system
# keeps state under `/var/lib` and logs under `/var/log`, and keeping to that is
# what lets a volume be mounted over each one the ordinary way instead of at a
# path only this application knows.
#
# The locks go to `/tmp` and nowhere else. A lock file only means anything while
# the process holding it is alive, and it is an `O_EXCL` create rather than a
# flock, so one left behind by a killed process is a stale file to be reported
# rather than a lock to wait on. The container's writable layer is discarded with
# the container, so a lock has nothing worth surviving it - and putting it on a
# volume would be the opposite of the point.
#
# Set as environment variables rather than compiled in, so running the same image
# outside a container puts them back beside the source.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_DIR=/var/lib/sawa9ly \
    LOG_DIR=/var/log/sawa9ly \
    LOCK_DIR=/tmp/sawa9ly \
    PYTHONPATH=/app

# A non-root user. The application writes to exactly the two directories above
# and to nothing else, so this costs one line rather than a policy.
RUN groupadd --system sawa9ly \
 && useradd --system --gid sawa9ly --home-dir /app --no-create-home sawa9ly

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The source. `PROJECT_ROOT` is derived from this file's own location and
# `DASHBOARD_DIST` is `PROJECT_ROOT/"dashboard"/"dist"`, so this layout is
# load-bearing rather than conventional: move `src/` and both the default
# database location and the dashboard location move with it.
COPY src/ ./src/
COPY cli/ ./cli/
COPY sawa9ly/ ./sawa9ly/
COPY main.py ./
COPY --from=dashboard /build/dist/ ./dashboard/dist/

# The CLI as a command, so a running container can be asked questions:
#
#   docker exec <container> sawa9ly-api user list
#
# chmod rather than relying on the file's own mode, because a checkout on Windows
# has no executable bit for a copy to preserve and the script would be copied as a
# 0644 file that the container cannot run.
COPY bin/sawa9ly-api /usr/local/bin/sawa9ly-api
RUN chmod 755 /usr/local/bin/sawa9ly-api

# Created here and owned by the runtime user, so a named volume mounted over
# either inherits that ownership when it is first created. That is what lets the
# SQLite profile write its database, and both profiles write their logs, without
# anything running as root. `/tmp/sawa9ly` is created too, since a volume is not
# mounted there and the directory has to exist before the queue or the bot starts.
RUN mkdir -p /var/lib/sawa9ly /var/log/sawa9ly /tmp/sawa9ly \
 && chown -R sawa9ly:sawa9ly /app /var/lib/sawa9ly /var/log/sawa9ly /tmp/sawa9ly

USER sawa9ly

EXPOSE 8000

# Only meaningful for the default command below, which serves HTTP. The bot and
# the queue do not, so compose turns this off for them rather than leaving three
# containers permanently unhealthy. It asks for /docs because that is the one
# route that is always present and never authenticated; a `/health` route was not
# added for the sake of a container check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('API_PORT', '8000') + '/docs', timeout=4)"]

# The API and the dashboard. One image, three processes: the bot and the queue
# override this, and they are the same image and the same code precisely so that
# there is one thing to build, tag and roll back.
#
# The tag says `api` and the image also runs the bot and the queue. That is the
# name the deployment and any registry use, so it is the name here too; the
# default command is the API because it is the one with a port and a health check
# and is the only one that makes sense to run bare.
CMD ["python", "main.py", "serve"]
