param(
    [switch] $Fix
)

$Root = Split-Path $PSScriptRoot -Parent
$RuffPath = Join-Path $Root "ruff.toml"
$RuffExe = Join-Path $Root ".py-env/venv/Scripts/ruff.exe"

if (-not (Test-Path $RuffExe)) {
    Write-Error "ruff was not found at $RuffExe. Run scripts/setup/setup_build_env.ps1 -Force to install it."
    exit 1
}

$Flag = ""
if ($Fix) {
    $Flag += "--fix"
}

# Anchored to $Root so the script works from any working directory, the same way $RuffPath is.
# prepare_patches.py lives outside the apworld but generates code that ships inside it, so it is
# held to the same rules.
$Targets = @(
    (Join-Path $Root "khimera_damg"),
    (Join-Path $Root "scripts/build/prepare_patches.py")
)

& $RuffExe check --config $RuffPath $Targets $Flag