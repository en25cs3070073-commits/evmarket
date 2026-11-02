#!/usr/bin/env bash
# Recreate the EV Analytics database and reload it from the generated CSV.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER=ev-postgres
DB=ev_analytics
USER=ev

docker compose -f "$ROOT/docker-compose.yml" up -d

echo "waiting for postgres..."
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" pg_isready -U "$USER" -d "$DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec "$CONTAINER" pg_isready -U "$USER" -d "$DB" >/dev/null || {
  echo "postgres did not become ready"; exit 1; }

docker cp "$ROOT/db/schema.sql"              "$CONTAINER:/tmp/schema.sql"
docker cp "$ROOT/db/load.sql"                "$CONTAINER:/tmp/load.sql"
docker cp "$ROOT/data/ev_market_dataset.csv" "$CONTAINER:/tmp/ev_market_dataset.csv"

# MSYS_NO_PATHCONV stops Git Bash rewriting container-side /tmp paths to Windows paths.
echo "files staged in container:"
MSYS_NO_PATHCONV=1 docker exec "$CONTAINER" ls -l /tmp

echo "applying schema..."
MSYS_NO_PATHCONV=1 docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1 -q -f /tmp/schema.sql

echo "loading data..."
MSYS_NO_PATHCONV=1 docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1 -f /tmp/load.sql
