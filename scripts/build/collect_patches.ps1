# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

$Root        = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$IncludeFile = Join-Path $Root "worlds\khimera_damg\patches\include.txt"
$PatchSource = Join-Path $Root "KhimeraDAMG-AP-Mod\releases"
$PatchDest   = Join-Path $Root "worlds\khimera_damg\patches"

if (-not (Test-Path $IncludeFile)) {
    throw "Patch include list not found at $IncludeFile"
}
if (-not (Test-Path $PatchSource)) {
    throw "Releases folder not found at $PatchSource. Is the KhimeraDAMG-AP-Mod submodule checked out?"
}

# Drop previously collected patches so a version removed from include.txt stops shipping.
Get-ChildItem -Path $PatchDest -Filter "*.zip" -File | Remove-Item -Force

$Versions = @(
    Get-Content $IncludeFile |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -ne "" -and -not $_.StartsWith("#") }
)

if ($Versions.Count -eq 0) {
    Write-Warning "No versions listed in include.txt; the apworld will ship with no patches."
}

foreach ($Version in $Versions) {
    $Source = Join-Path $PatchSource "$Version.zip"
    if (-not (Test-Path $Source)) {
        throw "include.txt lists '$Version' but $Source does not exist."
    }
    Copy-Item $Source (Join-Path $PatchDest "$Version.zip") -Force
    Write-Host "Collected patch $Version"
}