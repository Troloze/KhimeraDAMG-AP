# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Returns Archipelago\ from the prepared state to the development state.

.DESCRIPTION
    Removes the installed apworld from Archipelago\custom_worlds, along with a canary world a
    killed canary pass may have left there, deletes Archipelago\kdamg_prepared.json, and recreates
    the world link at Archipelago\worlds\khimera_damg. fuzz.py, hooks\ and empty.apworld stay, so
    the next scripts\fuzzer_prepare.ps1 reuses them.

    Does nothing when Archipelago\ is already in the development state. In any other state the
    script stops and points at scripts\restore_archipelago.ps1.
#>

. (Join-Path $PSScriptRoot "build\build_state.ps1")

$LinkScript = Join-Path $PSScriptRoot "setup\setup_world_link.ps1"

try {
    $State = Assert-BuildState -Allowed @("development", "prepared") -Action "Cleaning up after the fuzzer"
    if ($State.Name -eq "development") {
        if (Test-Path $KdamgCanaryApWorld) {
            Remove-Item $KdamgCanaryApWorld -Force -ErrorAction Stop
        }
        Write-Host "Archipelago\ is already in the development state."
        exit 0
    }

    foreach ($file in @($KdamgInstalledApWorld, $KdamgCanaryApWorld, $KdamgStateFile)) {
        if (Test-Path $file) {
            Remove-Item $file -Force -ErrorAction Stop
        }
    }

    & $LinkScript
    if ($LASTEXITCODE -ne 0) {
        throw "scripts\setup\setup_world_link.ps1 could not recreate the world link."
    }
    $null = Assert-BuildState -Allowed @("development") -Action "Cleaning up after the fuzzer"
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "Archipelago\ is back in the development state."
exit 0
