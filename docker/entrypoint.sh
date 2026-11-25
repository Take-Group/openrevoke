#!/bin/sh
# Runs before supervisor: applies the database migrations (python -m app.db migrate, under a
# PostgreSQL advisory lock). Compose waits for the PostgreSQL healthcheck, but the retry covers a
# database that is "up" and does not accept connections yet. Exit code 2 means the database
# cannot be migrated by this image (a newer version migrated it, or it predates migrations):
# retrying would not help, so the container stops with the message.
set -e

cd /app/backend

attempt=1
max_attempts=30

echo "[entrypoint] Migrating the database..."
while :; do
    rc=0
    /app/backend/.venv/bin/python -m app.db migrate || rc=$?
    [ "$rc" -eq 0 ] && break
    if [ "$rc" -eq 2 ]; then
        echo "[entrypoint] The database cannot be used by this version (see above)." >&2
        exit 1
    fi
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "[entrypoint] Database migration failed after ${max_attempts} attempts." >&2
        exit 1
    fi
    echo "[entrypoint] Attempt ${attempt}/${max_attempts} failed, retrying in 2s..."
    attempt=$((attempt + 1))
    sleep 2
done

echo "[entrypoint] Database ready. Starting API, worker and frontend."

cd /app
exec "$@"
