# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Runs one fuzzer pass and records its result. Called by scripts/run_fuzzer.ps1.

.DESCRIPTION
    A pass is one fuzz.py invocation with at most one checking hook loaded. Each of the fuzzer's
    checking hooks turns every outcome it does not test into a success or an OptionError, so
    loading two of them in the same run hides whatever the other one found. One hook per pass
    is the only arrangement whose result means anything.

    The pass table below says, for each pass, which hooks it loads, whether it may skip output,
    and whether the Empty world is added to every generation. The script checks the fuzzer
    environment for what that pass needs before starting, runs fuzz.py from the Archipelago
    folder, moves fuzz_output into the archive folder (fuzz.py wipes it at the start of every
    run), and writes result.json there with the counts, the verdict, and the most common errors.

    Exit codes: 0 when the verdict is "ok", 1 when it is "fail", 2 when the pass could not run
    or did not finish ("error" or "stalled").

.PARAMETER Pass
    The pass to run. One of the keys of the pass table below.

.PARAMETER ArchiveDir
    The run folder. The pass archives into a subfolder of it named after -Label.

.PARAMETER Label
    The name of the archive subfolder and of the pass in the summary. Defaults to -Pass.

.PARAMETER Game
    The apworld module name given to fuzz.py's -g.

.PARAMETER ExpectFailures
    Invert the verdict: the pass is "ok" only if at least one generation failed. Used for the
    canary world, which is broken on purpose.
#>

param(
    [Parameter(Mandatory = $true)]
    [string] $Pass,
    [Parameter(Mandatory = $true)]
    [string] $ArchiveDir,
    [string] $Label,
    [string] $Game = "khimera_damg",
    [int] $Runs = 500,
    [int] $Jobs = 16,
    [string] $Yamls = "1",
    [int] $Timeout = 15,
    [string] $Meta,
    [string[]] $ExtraArgs = @(),
    [switch] $ExpectFailures
)

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
# fuzz.py puts its own folder on sys.path to import Archipelago, so it runs from the Archipelago
# root, where scripts/fuzzer_prepare.ps1 copies it and the hooks.
. (Join-Path (Split-Path $PSScriptRoot -Parent) "build\build_state.ps1")
$FuzzRoot = Join-Path $Root "Archipelago"
$VenvPython = Join-Path $Root ".py-env\venv\Scripts\python.exe"
$FuzzOutput = Join-Path $FuzzRoot "fuzz_output"

# The index's acceptance bar: the failure rate must be below this.
$RateLimit = 0.01

# Kind "rate" is the measurement the index's 1% budget is about: no checking hook, output
# included, the Empty world in every generation. Kind "check" passes run one checking hook each,
# and any failure in them is a finding regardless of the rate.
#
# Empty comes from the fuzzer's own with_empty hook, the same route the index uses. It leaves
# outcomes untouched, so it is safe to combine with a checking hook. It is always listed first:
# if its worker setup fails, no hook gets registered and the failure surfaces unmasked.
#
# gerpocalypse cannot have Empty: it overwrites --with-static-worlds with a Kingdom Hearts YAML
# of its own, and needs that world installed.
#
# detect_output_placement_changes wraps generate_output, so its pass must not skip output.
#
# determinism generates every seed twice, the second time in a subprocess, so it gets half the
# jobs and twice the timeout.
$PassTable = [ordered] @{
    "rate" = @{
        Kind = "rate"; Hooks = @(); Empty = $true; SkipOutput = $false
    }
    "gerpocalypse" = @{
        Kind = "check"; Hooks = @("hooks.gerpocalypse:Hook"); Empty = $false; SkipOutput = $true
        NeedsKingdomHearts = $true
    }
    "indirect_conditions" = @{
        Kind = "check"; Hooks = @("hooks.indirect_conditions:Hook"); Empty = $true; SkipOutput = $true
    }
    "item_location_count" = @{
        Kind = "check"; Hooks = @("hooks.item_location_count:Hook"); Empty = $true; SkipOutput = $true
    }
    "detect_rule_variable_capture_issues" = @{
        Kind = "check"; Hooks = @("hooks.detect_rule_variable_capture_issues:Hook"); Empty = $true
        SkipOutput = $true
    }
    "check_placement_item_location_references" = @{
        Kind = "check"; Hooks = @("hooks.check_placement_item_location_references:Hook"); Empty = $true
        SkipOutput = $true
    }
    "detect_output_placement_changes" = @{
        Kind = "check"; Hooks = @("hooks.detect_output_placement_changes:Hook"); Empty = $true
        SkipOutput = $false
    }
    "determinism" = @{
        Kind = "check"; Hooks = @("hooks.determinism:Hook"); Empty = $true; SkipOutput = $true
        JobsDivisor = 2; TimeoutFactor = 2
    }
}

if (-not $Label) {
    $Label = $Pass
}
$PassDir = Join-Path $ArchiveDir $Label
New-Item -ItemType Directory -Path $PassDir -Force | Out-Null

$Notes = New-Object System.Collections.Generic.List[string]

function Write-Result {
    param(
        [string] $Verdict,
        [string] $Kind = "",
        [string] $Command = "",
        [int] $ExitCode = -1,
        $Stats = $null,
        $Rate = $null,
        [object[]] $Errors = @()
    )

    $result = [ordered] @{
        label = $Label
        pass = $Pass
        game = $Game
        kind = $Kind
        expect_failures = [bool] $ExpectFailures
        verdict = $Verdict
        exit_code = $ExitCode
        command = $Command
        stats = $Stats
        rate = $Rate
        notes = @($Notes)
        errors = @($Errors)
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $json = $result | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText((Join-Path $PassDir "result.json"), $json, $utf8NoBom)
}

function Stop-Pass {
    param([string] $Message)

    Write-Host "[$Label] $Message" -ForegroundColor Red
    $Notes.Add($Message)
    Write-Result -Verdict "error"
    exit 2
}

# --- Preflight --------------------------------------------------------------------------------

if (-not $PassTable.Contains($Pass)) {
    Stop-Pass "Unknown pass '$Pass'. Known passes: $($PassTable.Keys -join ', ')."
}
$Definition = $PassTable[$Pass]

if (-not (Test-Path $VenvPython)) {
    Stop-Pass "The build venv was not found at $VenvPython. Run scripts/setup.ps1 first."
}
# The prepared state, with a build that still matches khimera_damg\. It also guarantees that the
# world link is gone, without which the source would be fuzzed in place of the installed build.
try {
    $null = Assert-PreparedBuildCurrent -Action "The $Pass pass"
}
catch {
    Stop-Pass $_.Exception.Message
}

$Hooks = @()
if ($Definition.Empty) {
    $Hooks += "hooks.with_empty:Hook"
    if (-not (Test-Path (Join-Path $FuzzRoot "custom_worlds\empty.apworld"))) {
        Stop-Pass ("custom_worlds\empty.apworld is missing, so the Empty world cannot be added. " +
                   "Run scripts/fuzzer/build_empty_apworld.ps1, or scripts/fuzzer_prepare.ps1 again.")
    }
}
$Hooks += $Definition.Hooks

foreach ($hook in $Hooks) {
    $module = ($hook -split ":")[0]
    $file = Join-Path $FuzzRoot (($module -replace "\.", "\") + ".py")
    if (-not (Test-Path $file)) {
        Stop-Pass "Hook $hook is not in $FuzzRoot ($file). Run scripts/run_fuzzer.ps1 -Setup, then scripts/fuzzer_prepare.ps1."
    }
}

if ($Definition.NeedsKingdomHearts) {
    # The hook raises "kh1 needs to be loaded" inside each generation when the world is missing,
    # and its own reclassify_outcome then turns that error into a success. Without this check the
    # pass would report a clean result having tested nothing.
    $kh = (Test-Path (Join-Path $FuzzRoot "worlds\kh1")) -or
          (Test-Path (Join-Path $FuzzRoot "worlds\kh1.apworld")) -or
          (Test-Path (Join-Path $FuzzRoot "custom_worlds\kh1.apworld"))
    if (-not $kh) {
        Stop-Pass "gerpocalypse needs the Kingdom Hearts world (worlds\kh1), and $FuzzRoot has none."
    }
}

foreach ($argument in $ExtraArgs) {
    if ($argument -eq "--hook") {
        Stop-Pass "Hooks come from the pass table. Pass another -Pass instead of adding --hook to -ExtraArgs."
    }
    if ($argument -eq "--with-static-worlds" -and $Pass -eq "gerpocalypse") {
        Stop-Pass "gerpocalypse overwrites --with-static-worlds, so the worlds passed there would silently be dropped."
    }
    if ($argument -eq "--skip-output" -and -not $Definition.SkipOutput) {
        Stop-Pass "The $Pass pass must run generate_output, so --skip-output cannot be added to it."
    }
}

$PassJobs = $Jobs
if ($Definition.JobsDivisor) {
    $PassJobs = [Math]::Max(1, [int] [Math]::Floor($Jobs / $Definition.JobsDivisor))
}
$PassTimeout = $Timeout
if ($Definition.TimeoutFactor) {
    $PassTimeout = $Timeout * $Definition.TimeoutFactor
}

$FuzzArgs = @(
    "fuzz.py",
    "-r", "$Runs",
    "-j", "$PassJobs",
    "-g", $Game,
    "-n", $Yamls,
    "-t", "$PassTimeout"
)
if ($Meta) {
    $FuzzArgs += @("-m", $Meta)
}
if ($Definition.SkipOutput) {
    $FuzzArgs += "--skip-output"
}
if ($Definition.Kind -eq "rate") {
    # Ignored generations are excluded from the rate, so keep their YAMLs to check that what got
    # ignored really was an OptionError and not something hiding behind one.
    $FuzzArgs += "--dump-ignored"
}
foreach ($hook in $Hooks) {
    $FuzzArgs += @("--hook", $hook)
}
$FuzzArgs += $ExtraArgs

$Command = "$VenvPython " + (($FuzzArgs | ForEach-Object {
    if ($_ -match "\s") { "`"$_`"" } else { $_ }
}) -join " ")

# --- Run --------------------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Pass: $Label ===" -ForegroundColor Cyan
Write-Host $Command

if (Test-Path $FuzzOutput) {
    Remove-Item $FuzzOutput -Recurse -Force
}

Push-Location $FuzzRoot
try {
    & $VenvPython @FuzzArgs
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

# fuzz.py exit codes: 0 clean, 1 failures or timeouts, 2 crashed before reporting, 3 stalled
# (gave up on runs whose workers died; the report covers only the runs that came back).
$ReportPath = Join-Path $FuzzOutput "report.json"
$Report = $null
if (Test-Path $ReportPath) {
    $Report = Get-Content $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

if (Test-Path $FuzzOutput) {
    Get-ChildItem $FuzzOutput | Move-Item -Destination $PassDir -Force
    Remove-Item $FuzzOutput -Recurse -Force -ErrorAction SilentlyContinue
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $PassDir "command.txt"), "$Command`r`n", $utf8NoBom)

if ($null -eq $Report) {
    $Notes.Add("fuzz.py exited with code $ExitCode and wrote no report.json; it crashed before reporting.")
    Write-Result -Verdict "error" -Kind $Definition.Kind -Command $Command -ExitCode $ExitCode
    exit 2
}

# --- Verdict ----------------------------------------------------------------------------------

$Stats = $Report.stats
$Total = [int] $Stats.total
$Failures = [int] $Stats.failure
$Timeouts = [int] $Stats.timeout
$Ignored = [int] $Stats.ignored
$Unfinished = 0
if ($null -ne $Stats.unfinished) {
    $Unfinished = [int] $Stats.unfinished
}
$Bad = $Failures + $Timeouts

# Top errors, most frequent first. report.json keys them by game, then by message.
$Errors = @()
foreach ($gameEntry in $Report.errors.PSObject.Properties) {
    foreach ($errorEntry in $gameEntry.Value.PSObject.Properties) {
        $Errors += [pscustomobject] @{
            message = $errorEntry.Name
            count = @($errorEntry.Value).Count
            runs = @($errorEntry.Value | Select-Object -First 10)
        }
    }
}
$Errors = @($Errors | Sort-Object -Property count -Descending | Select-Object -First 5)

$Rate = $null
if ($Definition.Kind -eq "rate") {
    $Counted = $Total - $Ignored
    if ($Counted -gt 0) {
        $Rate = [Math]::Round($Bad / $Counted, 6)
    }
    if ($Ignored -gt 0) {
        $Notes.Add(("$Ignored generation(s) ended in an OptionError and were left out of the rate. " +
                    "This world rolls no invalid option combinations, so check the dumped YAMLs in the archive."))
    }
}

if ($Unfinished -gt 0) {
    $Notes.Add("$Unfinished run(s) never reported back and are not counted anywhere.")
}

if ($ExitCode -eq 3) {
    $Notes.Add("fuzz.py stalled: workers died and it gave up on their runs. The counts cover only what finished.")
    $Verdict = "stalled"
}
elseif ($ExitCode -eq 2) {
    $Notes.Add("fuzz.py exited with code 2, which means it crashed, but still wrote a report.")
    $Verdict = "error"
}
elseif ($Total -eq 0) {
    $Notes.Add("No generation finished.")
    $Verdict = "error"
}
elseif ($ExpectFailures) {
    if ($Failures -gt 0) {
        $Verdict = "ok"
    }
    else {
        $Notes.Add("This pass runs a world that is broken on purpose and should have failed, but nothing did.")
        $Verdict = "fail"
    }
}
elseif ($Definition.Kind -eq "rate") {
    if ($null -eq $Rate) {
        $Notes.Add("Every generation was ignored, so there is no rate.")
        $Verdict = "error"
    }
    elseif ($Rate -ge $RateLimit) {
        $Verdict = "fail"
    }
    else {
        $Verdict = "ok"
    }
}
elseif ($Bad -gt 0) {
    $Verdict = "fail"
}
else {
    $Verdict = "ok"
}

$StatsOut = [ordered] @{
    total = $Total
    success = [int] $Stats.success
    failure = $Failures
    timeout = $Timeouts
    ignored = $Ignored
    unfinished = $Unfinished
}
Write-Result -Verdict $Verdict -Kind $Definition.Kind -Command $Command -ExitCode $ExitCode `
    -Stats $StatsOut -Rate $Rate -Errors $Errors

if ($Verdict -eq "ok") {
    exit 0
}
if ($Verdict -eq "fail") {
    exit 1
}
exit 2
