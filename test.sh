#!/usr/bin/env bash
# Run from repo root: ./test.sh
exec "$(cd "$(dirname "$0")" && pwd)/scripts/test.sh" "$@"
