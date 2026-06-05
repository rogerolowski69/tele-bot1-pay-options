#!/usr/bin/env bash
# Run from repo root: ./dev-infra.sh -d
exec "$(cd "$(dirname "$0")" && pwd)/scripts/dev-infra.sh" "$@"
