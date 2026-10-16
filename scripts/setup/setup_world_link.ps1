# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [switch] $Force
)

$Root         = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$ApRoot       = Join-Path $Root "Archipelago"
$ApWorldsDir  = Join-Path $ApRoot "worlds"
$WorldSource  = Join-Path $Root "khimera_damg"
$LinkPath     = Join-Path $ApWorldsDir "khimera_damg"
$ExcludeEntry = "worlds/khimera_damg"

if (-not (Test-Path $WorldSource)) {
    Write-Error "Apworld source not found at $WorldSource"
    exit 1
}
if (-not (Test-Path $ApWorldsDir)) {
    Write-Error ("Archipelago is not set up: $ApWorldsDir is missing. " +
                 "Run scripts\setup\setup_archipelago.ps1 first.")
    exit 1
}

# With the built apworld installed (the prepared state, or what is left of it), a link would
# shadow it: Archipelago loads world folders first and skips an .apworld whose game is loaded.
# fuzzer_cleanup.ps1 and restore_archipelago.ps1 both remove it before they come here.
. (Join-Path (Split-Path $PSScriptRoot -Parent) "build\build_state.ps1")
if ((Test-Path $KdamgInstalledApWorld) -or (Test-Path $KdamgStateFile)) {
    Write-Error (Get-StateError -State (Get-BuildState) -Allowed @("development") -Action "Creating the world link")
    exit 1
}

# The Build APWorlds component resolves the world folder as worlds\<name> relative to the
# Archipelago root and only considers worlds loaded from a folder, so the apworld has to be
# reachable there. A link keeps the single source of truth in this repository.
$Existing = Get-Item $LinkPath -Force -ErrorAction SilentlyContinue
if ($Existing) {
    if (-not $Existing.LinkType) {
        Write-Error ("$LinkPath exists and is not a link. Remove it by hand, or run " +
                     "scripts\restore_archipelago.ps1; this script will not delete real files.")
        exit 1
    }
    # A link left over from an older layout still counts as present, so compare where it points.
    $CurrentTarget = [System.IO.Path]::GetFullPath(@($Existing.Target)[0]).TrimEnd("\")
    $Stale = $CurrentTarget -ne [System.IO.Path]::GetFullPath($WorldSource).TrimEnd("\")
    if (-not $Force -and -not $Stale) {
        Write-Host "World link already present: $LinkPath -> $CurrentTarget"
    }
    else {
        if ($Stale) {
            Write-Host "Replacing the world link at $LinkPath, which points at $CurrentTarget"
        }
        # DirectoryInfo.Delete() removes the reparse point itself. Remove-Item on a junction
        # has a history of recursing into the target on Windows PowerShell, so avoid it here.
        $Existing.Delete()
        $Existing = $null
    }
}

if (-not $Existing) {
    New-Item -ItemType Junction -Path $LinkPath -Target $WorldSource | Out-Null
    if (-not (Test-Path $LinkPath)) {
        Write-Error "Failed to create the world link at $LinkPath"
        exit 1
    }
    Write-Host "Created world link $LinkPath -> $WorldSource"
}

# The link is a per-clone artifact, and left alone it shows up as untracked in the Archipelago
# clone forever. info\exclude is the right home: it behaves like .gitignore but is local to the
# clone and survives restore_archipelago.ps1, which never touches the git directory. That lives
# outside the clone, at $KdamgApGitDir (from build_state.ps1).
if (-not (Test-Path (Join-Path $KdamgApGitDir "HEAD"))) {
    Write-Error ("The Archipelago clone's git directory is missing from $KdamgApGitDir. " +
                 "Run scripts\restore_archipelago.ps1.")
    exit 1
}

$ExcludeFile = Join-Path $KdamgApGitDir "info\exclude"
$InfoDir = Split-Path $ExcludeFile -Parent
if (-not (Test-Path $InfoDir)) {
    New-Item -ItemType Directory -Path $InfoDir | Out-Null
}

$ExistingLines = @()
if (Test-Path $ExcludeFile) {
    $ExistingLines = @(Get-Content $ExcludeFile)
}

if ($ExistingLines -contains $ExcludeEntry) {
    Write-Host "Exclude entry already present in $ExcludeFile"
}
else {
    # Append by hand rather than with Add-Content: Windows PowerShell's utf8 encoding writes a
    # BOM, and git would read that as part of the first pattern.
    $Payload = "$ExcludeEntry`n"
    if (Test-Path $ExcludeFile) {
        $Raw = [System.IO.File]::ReadAllText($ExcludeFile)
        if ($Raw.Length -gt 0 -and -not $Raw.EndsWith("`n")) {
            $Payload = "`n" + $Payload
        }
    }
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($ExcludeFile, $Payload, $Utf8NoBom)
    Write-Host "Added '$ExcludeEntry' to $ExcludeFile"
}

exit 0
