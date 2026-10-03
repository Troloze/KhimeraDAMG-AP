# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [switch] $Force
)

$Root         = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$ApRoot       = Join-Path $Root "Archipelago"
$ApWorldsDir  = Join-Path $ApRoot "worlds"
$WorldSource  = Join-Path $Root "worlds\khimera_damg"
$LinkPath     = Join-Path $ApWorldsDir "khimera_damg"
$ExcludeEntry = "worlds/khimera_damg"

if (-not (Test-Path $WorldSource)) {
    Write-Error "Apworld source not found at $WorldSource"
    exit 1
}
if (-not (Test-Path $ApWorldsDir)) {
    Write-Error "Archipelago submodule not checked out: $ApWorldsDir is missing. " +
                "Run git submodule update --init --recursive first."
    exit 1
}

# The Build APWorlds component resolves the world folder as worlds\<name> relative to the
# Archipelago root and only considers worlds loaded from a folder, so the apworld has to be
# reachable there. A link keeps the single source of truth in this repository.
$Existing = Get-Item $LinkPath -Force -ErrorAction SilentlyContinue
if ($Existing) {
    if (-not $Existing.LinkType) {
        Write-Error "$LinkPath exists and is not a link. Remove it by hand; this script will " +
                    "not delete real files inside the submodule."
        exit 1
    }
    if (-not $Force) {
        Write-Host "World link already present: $LinkPath -> $($Existing.Target)"
    }
    else {
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

# The link is a per-clone artifact. It cannot be committed to the submodule (that is a fork of
# Archipelago and off limits), and left alone it shows up as untracked there forever. info\exclude
# is the right home: it behaves like .gitignore but is local to the clone and never pushed.
$GitDir = & git -C $ApRoot rev-parse --absolute-git-dir
if ($LASTEXITCODE -ne 0 -or -not $GitDir) {
    Write-Error "Could not resolve the Archipelago submodule's git directory."
    exit 1
}

$ExcludeFile = Join-Path $GitDir "info\exclude"
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
