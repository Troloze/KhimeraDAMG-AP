# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Puts Archipelago\ back to the commit it was set up at, then recreates the world link in it.

.DESCRIPTION
    Every tracked file is reset to that commit and everything else is deleted, ignored files
    included (logs, host.yaml, __pycache__). The world link is removed first so nothing reaches
    worlds\khimera_damg through it, and created again at the end.

    When the clone cannot be restored in place, the folder is deleted and the same commit is
    downloaded again. When there is no usable clone at all, this falls back to
    setup\setup_archipelago.ps1 -Force, which downloads its default tag.

.PARAMETER Reclone
    Skip the in-place restore: delete the folder and download the pinned commit again.
#>

param(
    [switch] $Reclone
)

. (Join-Path $PSScriptRoot "setup\repository.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Path = Join-Path $Root "Archipelago"
$SetupScript = Join-Path $PSScriptRoot "setup\setup_archipelago.ps1"
$LinkScript = Join-Path $PSScriptRoot "setup\setup_world_link.ps1"

try {
    $Restored = Invoke-RepositoryRestore -Name "Archipelago" -Path $Path -Reclone:$Reclone
}
catch {
    Write-Error "Restoring Archipelago failed: $($_.Exception.Message)"
    exit 1
}

if (-not $Restored) {
    Write-Host "No usable clone to restore at $Path; setting it up from scratch."
    # The setup script creates the world link itself.
    & $SetupScript -Force
    exit $LASTEXITCODE
}

& $LinkScript
exit $LASTEXITCODE
