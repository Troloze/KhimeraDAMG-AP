
$Root = Split-Path $PSScriptRoot -Parent
$WorldFiles = Join-Path $Root "worlds\*"
$ZipName = "khimera_damg.zip"

$Destination = Join-Path $Root  $ZipName
$NewName = Join-Path $Root "khimera_damg.apworld"

Compress-Archive -Path $WorldFiles -DestinationPath $Destination -Force
Rename-Item $Destination $NewName