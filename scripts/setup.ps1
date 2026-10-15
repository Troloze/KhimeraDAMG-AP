# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [string] $PythonVersion = "3.13.15",
    [string] $ArchipelagoTag,
    [string] $ModTag,
    [switch] $Force
)

$SetupDir = Join-Path $PSScriptRoot "setup"

# The default tags live in each folder's own script. A tag is forwarded only when it was given,
# so an explicit -ModTag "" still means "latest commit" rather than "use the default".
$ArchipelagoArgs = @{}
if ($PSBoundParameters.ContainsKey("ArchipelagoTag")) {
    $ArchipelagoArgs["Tag"] = $ArchipelagoTag
}
$ModArgs = @{}
if ($PSBoundParameters.ContainsKey("ModTag")) {
    $ModArgs["Tag"] = $ModTag
}

# Order matters. setup_build_env installs Archipelago's requirements from the Archipelago clone,
# using the interpreter setup_python installs, so it runs last. The Archipelago step also creates
# the world link inside the clone.
$Steps = @(
    @{ Name = "Python interpreter"; Script = "setup_python.ps1";      Args = @{ Version = $PythonVersion } },
    @{ Name = "Archipelago";        Script = "setup_archipelago.ps1"; Args = $ArchipelagoArgs },
    @{ Name = "Game mod";           Script = "setup_mod.ps1";         Args = $ModArgs },
    @{ Name = "Build environment";  Script = "setup_build_env.ps1";   Args = @{} }
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
