# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Puts KhimeraDAMG-AP-Mod\ back to the commit it was set up at.

.DESCRIPTION
    Every tracked file is reset to that commit and everything else is deleted, ignored files
    included.

    When the clone cannot be restored in place, the folder is deleted and the same commit is
    downloaded again. When there is no usable clone at all, this falls back to
    setup\setup_mod.ps1 -Force, which downloads its default tag.

.PARAMETER Reclone
    Skip the in-place restore: delete the folder and download the pinned commit again.
#>

param(
    [switch] $Reclone
)

. (Join-Path $PSScriptRoot "setup\repository.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Path = Join-Path $Root "KhimeraDAMG-AP-Mod"
$SetupScript = Join-Path $PSScriptRoot "setup\setup_mod.ps1"

try {
    $Restored = Invoke-RepositoryRestore -Name "KhimeraDAMG-AP-Mod" -Path $Path -Reclone:$Reclone
}
catch {
    Write-Error "Restoring KhimeraDAMG-AP-Mod failed: $($_.Exception.Message)"
    exit 1
}

if (-not $Restored) {
    Write-Host "No usable clone to restore at $Path; setting it up from scratch."
    & $SetupScript -Force
    exit $LASTEXITCODE
}
exit 0
