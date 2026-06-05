#!/usr/bin/env pwsh
# Start full dev stack with debug tools (Adminer, Redis Commander, Dozzle, Mailpit)
#
# From repo root:
#   .\dev-up.ps1
#   .\scripts\dev-up.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$InfraDir = Join-Path $Root "infra"

if (-not (Test-Path $InfraDir)) {
    Write-Error "infra folder not found at '$InfraDir'. Run this from the repo root (bot1-pay-options)."
}

Push-Location $InfraDir
try {
    if (-not (Test-Path (Join-Path $Root ".env"))) {
        Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
        Write-Host "Created .env from .env.example — set BOT_TOKEN before testing payments."
    }

    $env:DOCKER_BUILDKIT = "1"
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"
    docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build @args
}
finally {
    Pop-Location
}