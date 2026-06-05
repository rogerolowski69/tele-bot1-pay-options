#!/usr/bin/env pwsh
# Run Acton CLI in WSL on Windows, or fail with instructions to use acton.sh on Linux.
# Usage: .\acton.ps1 test
#        .\acton.ps1 run deploy-emulation

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$TonDir = Join-Path $Root "ton"

if (-not (Test-Path $TonDir)) {
    Write-Error "ton/ Acton project not found at $TonDir"
}

$argString = ($args | ForEach-Object { "'$($_ -replace "'", "''")'" }) -join " "
if (-not $argString) { $argString = "--help" }

if ($IsLinux -or $IsMacOS) {
    & (Join-Path $Root "acton.sh") @args
    exit $LASTEXITCODE
}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL is required for Acton on Windows. Install WSL or run from Linux with ./acton.sh"
}

$WslTon = (wsl -e wslpath -a $TonDir).Trim()
wsl -e bash -lc "cd '$WslTon' && acton $argString"
