#!/usr/bin/env pwsh
# Deploy to TON testnet — requires: acton wallet new --name deployer --local --airdrop
& "$PSScriptRoot\..\acton.ps1" run deploy-testnet @args
