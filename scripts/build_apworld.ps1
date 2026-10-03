# AI-GENERATED FILE: Partially written by Claude (Anthropic), not fully hand-written by the developer.
param(
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) "py-env\Scripts\python.exe")
)

$Root       = Split-Path $PSScriptRoot -Parent
$Launcher   = Join-Path $Root "Archipelago\Launcher.py"
$Collect    = Join-Path $PSScriptRoot "build\collect_patches.ps1"
$GameName   = "Khimera: Destroy All Monster Girls"
$OutputFile = Join-Path $Root "build\apworlds\khimera_damg.apworld"

& $Collect

if (-not (Test-Path $Launcher)) {
    throw "Archipelago submodule not checked out: $Launcher is missing."
}
if (-not (Test-Path $PythonExe)) {
    throw "No build environment at $PythonExe. " +
          "Run scripts\setup.ps1 to create one, or pass -PythonExe."
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