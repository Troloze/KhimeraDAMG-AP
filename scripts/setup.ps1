# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [string] $PythonVersion = "3.13.15",
    [switch] $Force
)

$SetupDir = Join-Path $PSScriptRoot "setup"

# Order matters. setup_world_link only needs the submodule and fails in a second, so it runs
# before setup_build_env, which downloads a few hundred megabytes; setup_build_env in turn
# consumes the interpreter setup_python installs.
$Steps = @(
    @{ Name = "Python interpreter"; Script = "setup_python.ps1";     Args = @{ Version = $PythonVersion } },
    @{ Name = "World link";         Script = "setup_world_link.ps1"; Args = @{} },
    @{ Name = "Build environment";  Script = "setup_build_env.ps1";  Args = @{} }
)

$Step = 0
foreach ($Entry in $Steps) {
    $Step++
    $ScriptPath = Join-Path $SetupDir $Entry.Script

    if (-not (Test-Path $ScriptPath)) {
        Write-Error "Setup step $($Entry.Name) is missing: $ScriptPath"
        exit 1
    }

    Write-Host ""
    Write-Host "[$Step/$($Steps.Count)] $($Entry.Name) ($($Entry.Script))"

    $StepArgs = $Entry.Args.Clone()
    if ($Force) {
        $StepArgs["Force"] = $true
    }

    & $ScriptPath @StepArgs

    # The setup scripts report failure with "exit 1", which leaves $? true and only sets
    # $LASTEXITCODE, so that is what has to be checked.
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Setup step $($Entry.Name) failed with exit code $LASTEXITCODE. Stopping."
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "Setup complete. Build with scripts\build_apworld.ps1 (or build_and_replace.ps1)."
