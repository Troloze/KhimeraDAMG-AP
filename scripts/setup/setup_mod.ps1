# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

# Downloads the game-side mod into KhimeraDAMG-AP-Mod\ as a depth-1 clone.
#   -Tag "latest"  the highest version tag
#   -Tag ""        the newest commit on the default branch
#   -Tag <name>    that tag; an error if it does not exist
# An existing clone is left as it is unless -Force is given. scripts\restore_mod.ps1 puts it back
# to the commit it was set up at.

param(
    # The mod has no tags yet, so it follows the default branch.
    [string] $Tag = "",
    [switch] $Force
)

. (Join-Path $PSScriptRoot "repository.ps1")

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Path = Join-Path $Root "KhimeraDAMG-AP-Mod"
$Url = "https://github.com/Troloze/KhimeraDAMG-AP-Mod"

try {
    Invoke-RepositorySetup -Name "KhimeraDAMG-AP-Mod" -Url $Url -Path $Path -Tag $Tag -Force:$Force
}
catch {
    Write-Error "KhimeraDAMG-AP-Mod setup failed: $($_.Exception.Message)"
    exit 1
}
exit 0
