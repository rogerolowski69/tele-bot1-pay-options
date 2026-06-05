#!/usr/bin/env bash
# Run from repo root: ./dev-up.sh
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
exec "$(cd "$(dirname "$0")" && pwd)/scripts/dev-up.sh" "$@"
