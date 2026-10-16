# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Runs the apworld's own unit tests, and optionally Archipelago's core suite for this world.

.DESCRIPTION
    The tests live in khimera_damg/tests and are run with stdlib unittest through the
    build venv in .py-env\venv, so nothing extra has to be installed. Archipelago itself is imported
    from the submodule, and the apworld is reached through the junction that setup_world_link.ps1
    creates at Archipelago/worlds/khimera_damg.

    Nothing is written inside Archipelago/ or inside this repository:

      - the working directory is a throwaway folder under TEMP, seeded with a copy of the
        submodule's host.yaml when it has one, so the settings module loads that copy instead of
        creating one in the submodule;
      - PYTHONDONTWRITEBYTECODE stops __pycache__ folders appearing through the junction;
      - AP_TEST_WORLDS=khimera_damg keeps every other world out of the run, which also makes it
        about ten times faster.

.PARAMETER Core
    Run Archipelago's own test/general suite (scoped to this world) instead of the apworld tests.
    This is the suite the ionium index requires a world to pass.

.PARAMETER All
    Run the apworld tests and then the core suite.

.PARAMETER Area
    Only run one area of the suite: generation, client or guards. These are the folders under
    khimera_damg/tests.

.PARAMETER Filter
    Only run tests whose name matches this substring or glob (unittest's -k).

.PARAMETER Detailed
    Print one line per test instead of a dot.

.PARAMETER Durations
    Also report the slowest tests. Individual tests are meant to stay well under a second.

.EXAMPLE
    scripts/run_tests.ps1
    scripts/run_tests.ps1 -Area client -Detailed
    scripts/run_tests.ps1 -Filter "*ack*"
    scripts/run_tests.ps1 -All
#>

param(
    [switch] $Core,
    [switch] $All,
    [ValidateSet("generation", "client", "guards")]
    [string] $Area,
    [string] $Filter,
    [switch] $Detailed,
    [switch] $Durations,
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) ".py-env\venv\Scripts\python.exe")
)

$Root = Split-Path $PSScriptRoot -Parent
$ApRoot = Join-Path $Root "Archipelago"
$WorldLink = Join-Path $ApRoot "worlds\khimera_damg"
$TestsDir = Join-Path $WorldLink "tests"
$GeneralDir = Join-Path $ApRoot "test\general"
$HostYaml = Join-Path $ApRoot "host.yaml"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found at $PythonExe. Run scripts/setup.ps1 first."
    exit 1
}
if (-not (Test-Path $WorldLink)) {
    Write-Error "The world link at $WorldLink is missing. Run scripts/setup/setup_world_link.ps1."
    exit 1
}
if (-not (Test-Path $TestsDir)) {
    Write-Error "No test package found at $TestsDir."
    exit 1
}

# A working directory of our own. Archipelago's settings module prefers options.yaml/host.yaml
# from the current directory when it is not the install folder, so a copy here keeps it from
# writing one into the submodule.
$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("kdamg-tests-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $Work | Out-Null
if (Test-Path $HostYaml) {
    Copy-Item $HostYaml (Join-Path $Work "host.yaml")
}

$OldTestWorlds = $env:AP_TEST_WORLDS
$OldPythonPath = $env:PYTHONPATH
$OldNoBytecode = $env:PYTHONDONTWRITEBYTECODE

$env:AP_TEST_WORLDS = "khimera_damg"
$env:PYTHONPATH = $ApRoot
$env:PYTHONDONTWRITEBYTECODE = "1"

function Invoke-Suite {
    param(
        [string] $Name,
        [string] $StartDirectory
    )

    $arguments = @("-B", "-m", "unittest", "discover", "-s", $StartDirectory, "-t", $ApRoot)
    if ($Detailed) {
        $arguments += "-v"
    }
    if ($Durations) {
        $arguments += @("--durations", "10")
    }
    if ($Filter) {
        $arguments += @("-k", $Filter)
    }

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $PythonExe @arguments
    return $LASTEXITCODE
}

$Failed = 0
Push-Location $Work
try {
    if (-not $Core) {
        $start = $TestsDir
        $name = "khimera_damg tests"
        if ($Area) {
            $start = Join-Path $TestsDir $Area
            $name = "khimera_damg tests ($Area)"
        }
        $code = Invoke-Suite -Name $name -StartDirectory $start
        if ($code -ne 0) { $Failed = $code }
    }
    if ($Core -or $All) {
        $code = Invoke-Suite -Name "Archipelago core suite (khimera_damg only)" -StartDirectory $GeneralDir
        if ($code -ne 0) { $Failed = $code }
    }
}
finally {
    Pop-Location
    $env:AP_TEST_WORLDS = $OldTestWorlds
    $env:PYTHONPATH = $OldPythonPath
    $env:PYTHONDONTWRITEBYTECODE = $OldNoBytecode
    Remove-Item $Work -Recurse -Force -ErrorAction SilentlyContinue
}

exit $Failed
