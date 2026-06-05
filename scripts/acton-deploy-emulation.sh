#!/usr/bin/env bash
# Local emulation deploy (no wallet/network required)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/acton.sh" run deploy-emulation "$@"
