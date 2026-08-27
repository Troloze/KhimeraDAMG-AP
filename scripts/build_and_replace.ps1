
$APCustomWorldDir = "C:/ProgramData/Archipelago/custom_worlds"

$Root = Split-Path $PSScriptRoot -Parent
$BuildScript = Join-Path $PSScriptRoot "build_apworld.ps1"

& $BuildScript

$WorldLocation = Join-Path $Root "khimera_damg.apworld"
$APCustomWorldLocation = Join-Path $APCustomWorldDir "khimera_damg.apworld"

Copy-Item $WorldLocation $APCustomWorldLocation -Force

Remove-Item $WorldLocation