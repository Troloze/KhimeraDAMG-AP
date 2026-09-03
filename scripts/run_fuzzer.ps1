# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [switch] $Setup,
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) "python\python.exe"),
    [string[]] $FuzzArgs = @("-r", "500", "-j", "16", "-g", "khimera_damg", "-n", "1", "--skip-output")
)

$Root = Split-Path $PSScriptRoot -Parent
$WorldFiles = Join-Path $Root "worlds\*"
$FuzzRoot = Join-Path $Root "_ignore_\ap-fuzz"
$FuzzerRepo = Join-Path $Root "fuzzer"
$CustomWorldsDir = Join-Path $FuzzRoot "custom_worlds"
$ApWorldPath = Join-Path $CustomWorldsDir "khimera_damg.apworld"
$Venv = Join-Path $FuzzRoot ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

$Hooks = @(
    "hooks.gerpocalypse:Hook",
    "hooks.indirect_conditions:Hook",
    "hooks.item_location_count:Hook",
    "hooks.detect_rule_variable_capture_issues:Hook",
    "hooks.check_placement_item_location_references:Hook",
    "hooks.detect_output_placement_changes:Hook"
)

if ($Setup) {
    if (-not (Test-Path $FuzzRoot)) {
        git -C (Join-Path $Root "Archipelago") worktree add --detach $FuzzRoot HEAD
    }
    if (Test-Path $FuzzerRepo) {
        Remove-Item $FuzzerRepo -Recurse -Force
    }
    git clone --depth 1 https://github.com/ionium-ap/Archipelago-fuzzer $FuzzerRepo
    # A nested .git makes the outer repo treat this whole directory as an opaque boundary,
    # so its own .gitignore below would never be consulted. Strip it so /fuzzer behaves like
    # a plain self-ignoring folder, the same as /python.
    Remove-Item (Join-Path $FuzzerRepo ".git") -Recurse -Force
    Set-Content -Path (Join-Path $FuzzerRepo ".gitignore") -Value "*" -Encoding utf8

    Copy-Item (Join-Path $FuzzerRepo "fuzz.py") $FuzzRoot -Force
    Copy-Item (Join-Path $FuzzerRepo "hooks") $FuzzRoot -Recurse -Force

    if (-not (Test-Path $VenvPython)) {
        & $PythonExe -m venv $Venv
        & $VenvPython -m pip install -r (Join-Path $FuzzRoot "requirements.txt")
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Error "Fuzzer environment not found at $FuzzRoot. Run with -Setup first."
    exit 1
}

# A directory link works for static analysis but not for the fuzzer: Archipelago's own
# worlds/__init__.py never extends worlds.__path__ for a bare custom_worlds folder, so a
# plain "import worlds" can never find a submodule living there (verified empirically, and
# true upstream too). Only .apworld zips get registered, via a dedicated meta-path finder.
# So build a real one fresh each run, the same way scripts/build_apworld.ps1 does.
if (-not (Test-Path $CustomWorldsDir)) {
    New-Item -ItemType Directory -Path $CustomWorldsDir | Out-Null
}
if (Test-Path $ApWorldPath) {
    Remove-Item $ApWorldPath -Force
}
$ZipPath = Join-Path $CustomWorldsDir "khimera_damg.zip"
Compress-Archive -Path $WorldFiles -DestinationPath $ZipPath -Force
Rename-Item $ZipPath $ApWorldPath

$HookArgs = @()
foreach ($hook in $Hooks) { $HookArgs += "--hook"; $HookArgs += $hook }

Push-Location $FuzzRoot
& $VenvPython fuzz.py @FuzzArgs @HookArgs
Pop-Location
