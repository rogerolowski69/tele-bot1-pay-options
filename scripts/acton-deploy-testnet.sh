#!/usr/bin/env bash
# Deploy to TON testnet — requires: acton wallet new --name deployer --local --airdrop
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/acton.sh" run deploy-testnet "$@"
