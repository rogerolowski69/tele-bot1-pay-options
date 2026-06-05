#!/usr/bin/env bash
# Run Acton CLI in ton/ (Linux/macOS). On Windows use ./acton.ps1 (WSL).
# Usage: ./acton.sh test
ROOT="$(cd "$(dirname "$0")" && pwd)"
TON_DIR="$ROOT/ton"

if [[ ! -d "$TON_DIR" ]]; then
  echo "ton/ Acton project not found at $TON_DIR" >&2
  exit 1
fi

cd "$TON_DIR"
if [[ $# -eq 0 ]]; then
  set -- --help
fi
exec acton "$@"
