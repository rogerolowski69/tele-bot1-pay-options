#!/usr/bin/env pwsh
# Run the matching task script for the current OS (.ps1 on Windows, .sh on Linux/macOS/WSL).
# Usage: scripts/os-run.ps1 dev-up | dev-infra | test | ...

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Task,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir

function Test-IsWindows {
    if ($IsWindows) { return $true }
    return $env:OS -eq "Windows_NT"
}

$Ps1Script = Join-Path $ScriptDir "$Task.ps1"
$ShScript = Join-Path $ScriptDir "$Task.sh"

if (Test-IsWindows) {
    if (-not (Test-Path $Ps1Script)) {
        Write-Error "Missing Windows script: $Ps1Script"
    }
    & $Ps1Script @Rest
    exit $LASTEXITCODE
}

if (-not (Test-Path $ShScript)) {
    Write-Error "Missing Unix script: $ShScript"
}

if (Get-Command bash -ErrorAction SilentlyContinue) {
    & bash $ShScript @Rest
    exit $LASTEXITCODE
}

Write-Error "bash is required to run $ShScript on non-Windows platforms."
