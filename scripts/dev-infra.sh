#!/usr/bin/env bash
# Infra + debug tools only (Postgres, Redis, Adminer, Redis Commander, Dozzle, Mailpit)
# From repo root: ./dev-infra.sh -d
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra"

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker compose -f docker-compose.yml -f docker-compose.debug.yml up \
  postgres redis adminer redis-commander dozzle mailpit "$@"
