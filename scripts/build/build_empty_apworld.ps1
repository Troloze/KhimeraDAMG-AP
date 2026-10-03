# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [switch] $Force
)

$Root        = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$FuzzRoot    = Join-Path $Root "_ignore_\ap-fuzz"
$Clone       = Join-Path $Root "_ignore_\empty-apworld"
$WorldSource = Join-Path $Clone "empty"
$FilesPy     = Join-Path $FuzzRoot "worlds\Files.py"
$Stage       = Join-Path $Root "_ignore_\empty-build"
$OutputFile  = Join-Path $FuzzRoot "custom_worlds\empty.apworld"
$StaticDir   = Join-Path $FuzzRoot "static_worlds"
$StaticYaml  = Join-Path $StaticDir "empty.yaml"
$RepoUrl     = "https://github.com/ionium-ap/empty-apworld"

if (-not (Test-Path $FilesPy)) {
    throw "Fuzzer worktree not found at $FuzzRoot. Run scripts\run_fuzzer.ps1 -Setup first."
}

# Everything here lives under _ignore_\, which the root .gitignore excludes wholesale, so unlike
# the fuzzer clone in /fuzzer this one can keep its own .git and be pulled or re-pinned by hand.
if ((Test-Path $Clone) -and $Force) {
    Remove-Item $Clone -Recurse -Force
}
if (-not (Test-Path $Clone)) {
    git clone --depth 1 $RepoUrl $Clone
    if ($LASTEXITCODE -ne 0) {
        throw "git clone of $RepoUrl failed."
    }
}
if (-not (Test-Path $WorldSource)) {
    throw "The clone at $Clone has no empty\ folder; the upstream layout must have changed."
}

# empty-apworld's archipelago.json omits version/compatible_version exactly the way ours does,
# and APWorldContainer.read() raises InvalidDataError without them. Archipelago's build component
# injects both from container_version in worlds/Files.py, so read that out of the very worktree
# this artifact is going to be loaded by rather than hardcoding a number that can move upstream.
$Match = Select-String -Path $FilesPy -Pattern 'container_version:\s*int\s*=\s*(\d+)' | Select-Object -First 1
if (-not $Match) {
    throw "Could not find container_version in $FilesPy."
}
$ContainerVersion = [int] $Match.Matches[0].Groups[1].Value

if (Test-Path $Stage) {
    Remove-Item $Stage -Recurse -Force
}
New-Item -ItemType Directory -Path $Stage | Out-Null
Copy-Item $WorldSource (Join-Path $Stage "empty") -Recurse
Get-ChildItem -Path $Stage -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

$ManifestPath = Join-Path $Stage "empty\archipelago.json"
$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$Manifest | Add-Member -NotePropertyName "version" -NotePropertyValue $ContainerVersion -Force
$Manifest | Add-Member -NotePropertyName "compatible_version" -NotePropertyValue $ContainerVersion -Force

# Add-Content -Encoding utf8 writes a BOM on PowerShell 5.1; json.load tolerates one, but the
# no-BOM .NET writer is what setup_world_link.ps1 already uses for the same reason.
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ManifestPath, ($Manifest | ConvertTo-Json -Compress -Depth 10), $Utf8NoBom)

# Compress-Archive refuses any destination that is not named .zip, so build it under the name it
# wants and rename. Pointing it at the staged empty\ folder makes that folder the archive root,
# which is what the meta-path finder expects: one top-level package directory per .apworld.
$Zip = Join-Path $Stage "empty.zip"
Compress-Archive -Path (Join-Path $Stage "empty") -DestinationPath $Zip -Force

$OutputDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}
Move-Item $Zip $OutputFile -Force
Remove-Item $Stage -Recurse -Force

# fuzz.py copies every file in --with-static-worlds into each generation's yaml folder, so this
# yaml is what guarantees an Empty slot in every multiworld rather than in a random subset of
# them. That is the condition the index measures the failure rate under: 100 start-accessible
# locations present, so a failure points at real logic trouble and not at a restrictive start.
if (-not (Test-Path $StaticDir)) {
    New-Item -ItemType Directory -Path $StaticDir | Out-Null
}
$Yaml = @(
    "name: EmptyFiller",
    "game: Empty",
    "Empty: {}"
) -join "`n"
[System.IO.File]::WriteAllText($StaticYaml, "$Yaml`n", $Utf8NoBom)

# A manifest the container cannot read is the exact failure this script exists to avoid, and the
# fuzzer would just silently run without the world, so load it the way Archipelago will.
$VenvPython = Join-Path $FuzzRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Probe = "from worlds.Files import APWorldContainer; " +
             "c = APWorldContainer(r'$OutputFile'); c.read(); print(c.game)"
    Push-Location $FuzzRoot
    try {
        $Output = & $VenvPython -c $Probe
    } finally {
        Pop-Location
    }
    $Game = $Output | Select-Object -Last 1
    if ($Game -ne "Empty") {
        throw "Built $OutputFile but APWorldContainer.read() gave game '$Game' instead of 'Empty'."
    }
}

Write-Host "Placed $OutputFile (container version $ContainerVersion)"
Write-Host "Static world yaml at $StaticYaml"
