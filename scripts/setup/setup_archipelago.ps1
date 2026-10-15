# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

# Downloads Archipelago into Archipelago\ as a depth-1 clone, then creates the world link inside
# it through setup_world_link.ps1.
#   -Tag "latest"  the highest version tag
#   -Tag ""        the newest commit on the default branch
#   -Tag <name>    that tag; an error if it does not exist
# An existing clone is left as it is unless -Force is given. scripts\restore_archipelago.ps1 puts
# it back to the commit it was set up at.

param(
    [string] $Tag = "0.6.8",
    [switch] $Force
)

. (Join-Path $PSScriptRoot "repository.ps1")

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Path = Join-Path $Root "Archipelago"
# Upstream rather than the Troloze fork: the fork carries no tags, so only -Tag "" resolves there.
$Url = "https://github.com/ArchipelagoMW/Archipelago"

try {
    Invoke-RepositorySetup -Name "Archipelago" -Url $Url -Path $Path -Tag $Tag -Force:$Force
}
catch {
    Write-Error "Archipelago setup failed: $($_.Exception.Message)"
    exit 1
}

# A replaced folder took its link with it, so this runs every time. It is a no-op when the link
# is already there.
& (Join-Path $PSScriptRoot "setup_world_link.ps1")
exit $LASTEXITCODE
