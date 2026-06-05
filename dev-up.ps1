# Run from repo root:  .\dev-up.ps1
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
& "$PSScriptRoot\scripts\dev-up.ps1" @args
