#!/usr/bin/env bash
# =============================================================================
# OntDekker — guide-service container entrypoint
#
# Startup sequence:
#   1. Wait for PostgreSQL to accept connections (pg_isready, no sleep timers).
#   2. Run Alembic migrations (idempotent — skips if already at head).
#   3. Exec uvicorn as PID 1 so the process receives OS signals correctly.
#
# Environment variables (injected by docker-compose):
#   DATABASE_URL  — full asyncpg DSN, e.g.
#                   postgresql+asyncpg://postgres:postgres@postgres:5432/guide_db
# =============================================================================
set -e

# ---------------------------------------------------------------------------
# 1. Parse host and port from DATABASE_URL for pg_isready probing.
#    Expected format: postgresql+asyncpg://user:pass@host:port/dbname
# ---------------------------------------------------------------------------
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+):?([0-9]*).*|\1|')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*@[^:]+:([0-9]+)/.*|\1|')
DB_USER=$(echo "$DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')

# Default port if not specified
DB_PORT="${DB_PORT:-5432}"

echo "[guide-service] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

MAX_RETRIES=30
RETRY_INTERVAL=2
attempt=0

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
        echo "[guide-service] ERROR: PostgreSQL not ready after ${MAX_RETRIES} attempts. Aborting."
        exit 1
    fi
    echo "[guide-service] PostgreSQL not ready yet (attempt ${attempt}/${MAX_RETRIES}). Retrying in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

echo "[guide-service] PostgreSQL is ready."

# ---------------------------------------------------------------------------
# 2. Run Alembic migrations.
#    alembic upgrade head is idempotent — it is a no-op if already at head.
# ---------------------------------------------------------------------------
echo "[guide-service] Running Alembic migrations..."
alembic upgrade head
echo "[guide-service] Migrations complete."

# ---------------------------------------------------------------------------
# 3. Start the application server.
#    exec replaces this shell process so uvicorn becomes PID 1 and correctly
#    receives SIGTERM/SIGINT from Docker for graceful shutdown.
# ---------------------------------------------------------------------------
echo "[guide-service] Starting uvicorn..."
exec uvicorn app.core.main:app --host 0.0.0.0 --port 8000
