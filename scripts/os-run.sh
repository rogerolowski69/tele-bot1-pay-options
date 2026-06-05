#!/usr/bin/env bash
# Run the matching task script for the current OS (.ps1 on Windows, .sh on Linux/macOS).
# Usage: scripts/os-run.sh dev-up | dev-infra | test | acton-test | ...
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: os-run.sh <task> [args...]" >&2
  echo "Tasks: dev-up, dev-infra, test, acton, acton-test, acton-deploy-emulation, acton-deploy-testnet" >&2
  exit 1
fi

TASK="$1"
shift

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

is_windows() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
  esac
  [[ "${OS:-}" == "Windows_NT" ]] && return 0
  return 1
}

PS1_SCRIPT="$SCRIPT_DIR/${TASK}.ps1"
SH_SCRIPT="$SCRIPT_DIR/${TASK}.sh"

if is_windows; then
  if [[ ! -f "$PS1_SCRIPT" ]]; then
    echo "Missing Windows script: $PS1_SCRIPT" >&2
    exit 1
  fi
  if command -v pwsh >/dev/null 2>&1; then
    exec pwsh -NoLogo -File "$PS1_SCRIPT" "$@"
  fi
  if command -v powershell >/dev/null 2>&1; then
    exec powershell -NoLogo -File "$PS1_SCRIPT" "$@"
  fi
  echo "PowerShell (pwsh) is required on Windows." >&2
  exit 1
fi

if [[ ! -f "$SH_SCRIPT" ]]; then
  echo "Missing Unix script: $SH_SCRIPT" >&2
  exit 1
fi
exec bash "$SH_SCRIPT" "$@"
