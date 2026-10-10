# AI-GENERATED FILE: Partially written by Claude (Anthropic), not fully hand-written by the developer.
param(
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) "py-env\Scripts\python.exe")
)

$Root        = Split-Path $PSScriptRoot -Parent
$Launcher    = Join-Path $Root "Archipelago\Launcher.py"
$Prepare     = Join-Path $PSScriptRoot "build\prepare_patches.py"
$GameName    = "Khimera: Destroy All Monster Girls"
$OutputFile  = Join-Path $Root "build\apworlds\khimera_damg.apworld"
$PatchSource = Join-Path $Root "KhimeraDAMG-AP-Mod\releases"
$PatchDest   = Join-Path $Root "worlds\khimera_damg\patches"

if (-not (Test-Path $Launcher)) {
    throw "Archipelago submodule not checked out: $Launcher is missing."
}
if (-not (Test-Path $PythonExe)) {
    throw "No build environment at $PythonExe. " +
          "Run scripts\setup.ps1 to create one, or pass -PythonExe."
}

# Refreshes the collected release zips and regenerates patches\data.py. It runs after the guards
# above because it needs $PythonExe, and its exit code is checked because it leaves the previous
# data.py and zips untouched when it fails -- without this the build would carry on and package
# stale tables while still reporting success.
& $PythonExe $Prepare $PatchSource $PatchDest
if ($LASTEXITCODE -ne 0) {
    throw "prepare_patches.py failed. Check the output above."
}

# Launcher.py calls ModuleUpdate.update() on import, which blocks on stdin asking to pip-install
# anything it considers unsatisfied. setup_build_env.ps1 already owns the environment, so opt out
# rather than risk a build hanging on a prompt nobody can see.
$env:SKIP_REQUIREMENTS_UPDATE = "1"

# The component logs an error and exits 0 if it doesn't recognise the game name,
# so clear the old artifact and verify a new one appeared.
if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

Push-Location $Root
try {
    & $PythonExe $Launcher "Build APWorlds" -- --skip_open_folder $GameName
} finally {
    Pop-Location
    Remove-Item Env:\SKIP_REQUIREMENTS_UPDATE -ErrorAction SilentlyContinue
}

if (-not (Test-Path $OutputFile)) {
    throw "Build APWorlds produced no artifact at $OutputFile. Check the output above."
}

Write-Host "Built $OutputFile"