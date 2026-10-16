# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Runs Archipelago's full core suite against the built apworld, the way the ionium index does.

.DESCRIPTION
    The index requires a world to pass all of Archipelago's core unit tests with its .apworld
    installed. This runs test/general from the Archipelago root, over every world, with the
    apworld that scripts/fuzzer_prepare.ps1 built and installed in Archipelago/custom_worlds.

    It needs Archipelago/ in the prepared state, and refuses a build that no longer matches
    khimera_damg/ (scripts/build/build_state.ps1); run scripts/fuzzer_prepare.ps1 first, and
    scripts/fuzzer_cleanup.ps1 when done. scripts/run_tests.ps1 -Core is the quick version: the same
    suite scoped to this world, against the source through the world link.

    It runs from the Archipelago root like the index does, so Archipelago writes its usual logs and
    host.yaml there. -B keeps __pycache__ folders out.

    The -t . matters: without a top-level directory, unittest imports the test modules as
    top-level modules instead of test.general.*, and several of them then fail to import whatever
    the world does. Takes about 90 seconds.

.PARAMETER Filter
    Only run tests whose name matches this substring or glob (unittest's -k).

.PARAMETER Detailed
    Print one line per test instead of a dot.

.EXAMPLE
    scripts/fuzzer_prepare.ps1
    scripts/run_index_tests.ps1
    scripts/fuzzer_cleanup.ps1
#>

param(
    [string] $Filter,
    [switch] $Detailed,
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) ".py-env\venv\Scripts\python.exe")
)

. (Join-Path $PSScriptRoot "build\build_state.ps1")

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found at $PythonExe. Run scripts/setup.ps1 first."
    exit 1
}
try {
    $Recorded = Assert-PreparedBuildCurrent -Action "Running the core suite against the built apworld"
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}

$Arguments = @("-B", "-m", "unittest", "discover", "-s", "test/general", "-t", ".")
if ($Detailed) {
    $Arguments += "-v"
}
if ($Filter) {
    $Arguments += @("-k", $Filter)
}

# The index runs every world. AP_TEST_WORLDS, if it is set in this shell, would scope the run.
$OldTestWorlds = $env:AP_TEST_WORLDS
Remove-Item Env:\AP_TEST_WORLDS -ErrorAction SilentlyContinue

Write-Host "Core suite against $KdamgInstalledApWorld (prepared $($Recorded.prepared_at))" -ForegroundColor Cyan
Push-Location $KdamgApRoot
try {
    & $PythonExe @Arguments
    $Code = $LASTEXITCODE
}
finally {
    Pop-Location
    if ($null -ne $OldTestWorlds) {
        $env:AP_TEST_WORLDS = $OldTestWorlds
    }
}
exit $Code
