#!/usr/bin/env pwsh
# Run Acton CLI in WSL (Acton is installed in Ubuntu, not Windows PATH).
# Usage: .\acton.ps1 test
#        .\acton.ps1 run deploy-emulation
#        .\acton.ps1 script contracts/scripts/deploy.tolk --net testnet --tonconnect

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$TonDir = Join-Path $Root "ton"
$WslTon = "/mnt/c/Users/roger/Documents/code/telegram-bot/bot1-pay-options/ton"

if (-not (Test-Path $TonDir)) {
    Write-Error "ton/ Acton project not found at $TonDir"
}

$argString = ($args | ForEach-Object { "'$_'" }) -join " "
if (-not $argString) { $argString = "--help" }

wsl -e bash -lc "cd '$WslTon' && acton $argString"
