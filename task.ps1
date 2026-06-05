#!/usr/bin/env pwsh
# Cross-platform task runner (Windows PowerShell).
# Usage: .\task.ps1 dev-up | dev-infra | test | acton-test
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Task,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

& "$PSScriptRoot\scripts\os-run.ps1" $Task @Rest
exit $LASTEXITCODE
