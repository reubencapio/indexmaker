#!/bin/sh
# Container entrypoint.
#
# Migrations run here rather than as a supervisord program. Supervisord's
# `priority` only orders *starts*; it does not wait. The old arrangement let
# uvicorn begin serving while `alembic upgrade head` was still running, so a
# request could hit a table that did not have its columns yet -- and because the
# migrations program was `autorestart=false`, a failure was silent except in the
# logs.
#
# Running them here makes the ordering real and the failure loud: if migrations
# fail, the container never starts, and the platform reports a failed deploy
# instead of serving a half-migrated schema.

set -e

# Exactly one service should migrate. With the API and the worker deployed as
# separate services off the same image, both would otherwise run `alembic upgrade
# head` at the same moment and race each other on the version table.
: "${RUN_MIGRATIONS:=true}"

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "[entrypoint] Running database migrations..."
    python -m alembic upgrade head
    echo "[entrypoint] Migrations complete."
else
    echo "[entrypoint] Skipping migrations (RUN_MIGRATIONS=false)."
fi

# Redis runs in-container by default so a single-service deployment works out of
# the box. Point REDIS_URL at a managed instance and set RUN_LOCAL_REDIS=false:
# the in-container broker loses every queued job when the container restarts,
# which on a deploy means silently dropping work that was already accepted.
: "${RUN_LOCAL_REDIS:=true}"

# The worker runs alongside the API by default. Set RUN_WORKER=false here and
# deploy a second service with RUN_WORKER=true / RUN_API=false to scale them
# independently.
: "${RUN_WORKER:=true}"
: "${RUN_API:=true}"

export RUN_LOCAL_REDIS RUN_WORKER RUN_API

echo "[entrypoint] redis=${RUN_LOCAL_REDIS} worker=${RUN_WORKER} api=${RUN_API}"

exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
