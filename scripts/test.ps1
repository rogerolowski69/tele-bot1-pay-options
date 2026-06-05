#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    uv run pytest tests/ -v @args
} finally {
    Pop-Location
}
