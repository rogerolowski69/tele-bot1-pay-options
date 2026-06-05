#!/usr/bin/env pwsh
# Infra + debug tools only (Postgres, Redis, Adminer, Redis Commander, Dozzle, Mailpit)
#
# From repo root:
#   .\dev-infra.ps1 -d
#   .\scripts\dev-infra.ps1 -d

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$InfraDir = Join-Path $Root "infra"

if (-not (Test-Path $InfraDir)) {
    Write-Error "infra folder not found at '$InfraDir'. Run this from the repo root (bot1-pay-options)."
}

Push-Location $InfraDir
try {
    $env:DOCKER_BUILDKIT = "1"
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"
    docker compose -f docker-compose.yml -f docker-compose.debug.yml up postgres redis adminer redis-commander dozzle mailpit @args
}
finally {
    Pop-Location
}