#!/usr/bin/env bash
# Start full dev stack with debug tools (Adminer, Redis Commander, Dozzle, Mailpit)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env from .env.example — set BOT_TOKEN before testing payments."
fi

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build "$@"
