# Replace if needed
$APCustomWorldDir = "C:/ProgramData/Archipelago/custom_worlds"

$Root = Split-Path $PSScriptRoot -Parent
$BuildScript = Join-Path $PSScriptRoot "build_apworld.ps1"

& $BuildScript

$WorldLocation = Join-Path $Root "Archipelago\build\apworlds\khimera_damg.apworld"
$APCustomWorldLocation = Join-Path $APCustomWorldDir "khimera_damg.apworld"

# Left in place: Archipelago\ is disposable, and restore_archipelago.ps1 clears it.
Copy-Item $WorldLocation $APCustomWorldLocation -Force