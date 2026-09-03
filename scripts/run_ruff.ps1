
$Root = Split-Path $PSScriptRoot -Parent
$RuffPath = Join-Path $Root "ruff.toml"

# Updated ruff raises issues on files irrelevant to this PR.
# Remove this comment before doing the PR.
# & ruff check --config $RuffPath "worlds/khimera_damg"