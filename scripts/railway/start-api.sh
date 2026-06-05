#!/usr/bin/env sh
set -eu

PORT="${PORT:-8000}"

# Railway Postgres plugin uses postgresql:// — SQLAlchemy async needs asyncpg driver
case "${DATABASE_URL:-}" in
  postgresql://*)
    export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
    ;;
esac

exec uv run uvicorn apps.api.main:app --host 0.0.0.0 --port "$PORT"
