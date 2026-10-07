param(
    [switch] $Fix 
)

$Root = Split-Path $PSScriptRoot -Parent
$RuffPath = Join-Path $Root "ruff.toml"

# Updated ruff raises issues on files irrelevant to this PR.
# Remove this comment before doing the PR.

$Flag = ""
if ($Fix) {
    $Flag = "--fix"
}

# Anchored to $Root so the script works from any working directory, the same way $RuffPath is.
# prepare_patches.py lives outside the apworld but generates code that ships inside it, so it is
# held to the same rules.
$Targets = @(
    (Join-Path $Root "worlds/khimera_damg"),
    (Join-Path $Root "scripts/build/prepare_patches.py")
)

& ruff check --config $RuffPath $Targets $Flag

