# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Builds, or removes, the canary world the fuzzer pipeline is checked against.

.DESCRIPTION
    The canary is a tiny world that is broken on purpose: its item pool is one item short of its
    location count, and its victory needs an item that does not exist. A fuzzer pass over it has
    to report failures. If it reports none, the pipeline is hiding them, which is exactly what the
    old all-hooks-at-once invocation did for months without anyone noticing.

    The world is written from scratch here and packed into
    fuzz-env\ap-fuzz\custom_worlds\kdamg_canary.apworld. It exists only in the fuzzer worktree,
    only for the length of a canary pass: scripts/run_fuzzer.ps1 builds it before the pass and
    removes it afterwards, so it is never loaded alongside a real measurement.

.PARAMETER Remove
    Delete the canary .apworld instead of building it.
#>

param(
    [switch] $Remove
)

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$FuzzRoot = Join-Path $Root "fuzz-env\ap-fuzz"
$FilesPy = Join-Path $FuzzRoot "worlds\Files.py"
$Stage = Join-Path $Root "fuzz-env\canary-build"
$OutputFile = Join-Path $FuzzRoot "custom_worlds\kdamg_canary.apworld"
$ModuleName = "kdamg_canary"
$GameName = "KDAMG Fuzzer Canary"

if ($Remove) {
    if (Test-Path $OutputFile) {
        Remove-Item $OutputFile -Force
    }
    return
}

if (-not (Test-Path $FilesPy)) {
    throw "Fuzzer worktree not found at $FuzzRoot. Run scripts\run_fuzzer.ps1 -Setup first."
}

# Same reason as in build_empty_apworld.ps1: APWorldContainer.read() needs version and
# compatible_version in the manifest, and the value has to match the worktree that loads it.
$Match = Select-String -Path $FilesPy -Pattern 'container_version:\s*int\s*=\s*(\d+)' | Select-Object -First 1
if (-not $Match) {
    throw "Could not find container_version in $FilesPy."
}
$ContainerVersion = [int] $Match.Matches[0].Groups[1].Value

$Source = @'
"""A world that is broken on purpose, for checking that the fuzzer pipeline reports failures.

Built by scripts/fuzzer/build_canary_apworld.ps1 into the fuzzer worktree only. Never install it.
"""

from BaseClasses import Item, ItemClassification, Location, Region
from Options import PerGameCommonOptions
from worlds.AutoWorld import World


class CanaryWorld(World):
    game = "KDAMG Fuzzer Canary"
    options_dataclass = PerGameCommonOptions
    location_name_to_id = {f"Canary Location {i}": 770000 + i for i in range(1, 11)}
    item_name_to_id = {f"Canary Item {i}": 770000 + i for i in range(1, 11)}

    def create_item(self, name: str) -> Item:
        return Item(name, ItemClassification.filler, self.item_name_to_id[name], self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        menu.add_locations(self.location_name_to_id, Location)
        self.multiworld.regions.append(menu)

    def create_items(self) -> None:
        # One item short of the location count: the item_location_count hook has to catch this.
        names = list(self.item_name_to_id)[:-1]
        self.multiworld.itempool += [self.create_item(name) for name in names]

    def set_rules(self) -> None:
        # No item by this name exists, so the seed can never be beaten: a plain generation fails.
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Canary Victory", self.player)
'@

$Manifest = [ordered] @{
    game = $GameName
    minimum_ap_version = "0.6.4"
    world_version = "0.0.1"
    authors = @("KhimeraDAMG-AP tooling")
    version = $ContainerVersion
    compatible_version = $ContainerVersion
}

if (Test-Path $Stage) {
    Remove-Item $Stage -Recurse -Force
}
$Package = Join-Path $Stage $ModuleName
New-Item -ItemType Directory -Path $Package | Out-Null

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $Package "__init__.py"), $Source, $Utf8NoBom)
[System.IO.File]::WriteAllText(
    (Join-Path $Package "archipelago.json"),
    ($Manifest | ConvertTo-Json -Compress),
    $Utf8NoBom
)

# Compress-Archive only writes .zip names, and the package folder has to be the archive root.
$Zip = Join-Path $Stage "$ModuleName.zip"
Compress-Archive -Path $Package -DestinationPath $Zip -Force

$OutputDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}
Move-Item $Zip $OutputFile -Force
Remove-Item $Stage -Recurse -Force

$VenvPython = Join-Path $FuzzRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Probe = "from worlds.Files import APWorldContainer; " +
             "c = APWorldContainer(r'$OutputFile'); c.read(); print(c.game)"
    Push-Location $FuzzRoot
    try {
        $Output = & $VenvPython -c $Probe
    }
    finally {
        Pop-Location
    }
    $Loaded = $Output | Select-Object -Last 1
    if ($Loaded -ne $GameName) {
        throw "Built $OutputFile but APWorldContainer.read() gave game '$Loaded' instead of '$GameName'."
    }
}

Write-Host "Placed $OutputFile (container version $ContainerVersion)"
