#!/usr/bin/env bash
# Cross-platform task runner (Linux/macOS/Git Bash on Windows).
# Usage: ./task.sh dev-up | dev-infra | test | acton-test
exec "$(cd "$(dirname "$0")" && pwd)/scripts/os-run.sh" "$@"
