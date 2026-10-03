# Replace if needed
$APCustomWorldDir = "C:/ProgramData/Archipelago/custom_worlds"

$Root = Split-Path $PSScriptRoot -Parent
$BuildScript = Join-Path $PSScriptRoot "build_apworld.ps1"

& $BuildScript

$WorldLocation = Join-Path $Root "build\apworlds\khimera_damg.apworld"
$APCustomWorldLocation = Join-Path $APCustomWorldDir "khimera_damg.apworld"

# Left in place: build\ is a gitignored output folder, not the repo root it used to litter.
Copy-Item $WorldLocation $APCustomWorldLocation -Force