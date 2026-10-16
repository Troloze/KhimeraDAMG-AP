# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Runs Eijebong's fuzzer (ionium-ap/Archipelago-fuzzer) against the apworld, one pass at a time.

.DESCRIPTION
    Fuzzes the built apworld inside Archipelago\. The passes need Archipelago\ in the prepared
    state, which scripts\fuzzer_prepare.ps1 enters: the apworld built and installed in
    Archipelago\custom_worlds, the world link removed, and fuzz.py, hooks\ and empty.apworld in
    place. This script never builds and never touches the world link. It refuses to run when
    Archipelago\ is not prepared, or when khimera_damg\ has changed since the prepare
    (scripts\build\build_state.ps1). scripts\fuzzer_cleanup.ps1 returns to the development state
    afterwards.

    The requested passes run through scripts\fuzzer\run_fuzz_pass.ps1. Every pass is archived
    under fuzzer\runs\<timestamp>\<pass>\ with its command line, fuzz.py's own output and a
    result.json. A summary table follows the last pass.

    Why passes: each checking hook turns every outcome it is not testing into a success or an
    OptionError, so a run with several hooks loaded cannot report a failure at all. The failure
    rate the index cares about comes from the "rate" pass alone, which loads no checking hook and
    puts the Empty world in every generation. See docs\Running the Fuzzer.md.

    Exit code: 0 when every pass came back "ok", 1 otherwise.

.PARAMETER Setup
    Refresh the fuzzer clone in fuzzer\ (keeping khimera_damg.yaml, empty-apworld\ and runs\),
    copy fuzz.py and hooks\ into Archipelago\, clone empty-apworld again and rebuild
    empty.apworld. Then stop, unless -Pass is also given. Works in the development and the
    prepared state, and changes neither.

.PARAMETER Pass
    One or more of:
      rate                                       the failure rate (the default)
      gerpocalypse, indirect_conditions, item_location_count, detect_rule_variable_capture_issues,
      check_placement_item_location_references, detect_output_placement_changes
                                                 one counted hook each
      determinism                                same seed twice, compared (not counted)
      checks                                     the six counted hooks, one pass each
      all                                        rate, then checks
      canary                                     a broken world, to prove failures get reported

.PARAMETER Runs
    Generations per pass. The canary is capped at 50, since every generation of it fails fast.

.PARAMETER Yamls
    Khimera YAMLs per generation: a number or a range such as "1-3". The Empty slot comes on top.

.PARAMETER Meta
    The fuzz-meta file. Defaults to fuzzer\khimera_damg.yaml, resolved to an absolute path
    because fuzz.py runs from Archipelago\.

.PARAMETER NoMeta
    Do not pass a fuzz-meta file.

.PARAMETER ExtraArgs
    Extra arguments for fuzz.py, added to every pass. --hook is refused: pick a pass instead.

.EXAMPLE
    scripts/run_fuzzer.ps1 -Setup
    scripts/fuzzer_prepare.ps1
    scripts/run_fuzzer.ps1
    scripts/run_fuzzer.ps1 -Pass checks -Runs 200
    scripts/run_fuzzer.ps1 -Pass canary
    scripts/fuzzer_cleanup.ps1
#>

param(
    [switch] $Setup,
    [string[]] $Pass,
    [int] $Runs = 500,
    [int] $Jobs = 16,
    [string] $Yamls = "1",
    [int] $Timeout = 15,
    [string] $Meta = (Join-Path (Split-Path $PSScriptRoot -Parent) "fuzzer\khimera_damg.yaml"),
    [switch] $NoMeta,
    [string[]] $ExtraArgs = @()
)

. (Join-Path $PSScriptRoot "build\build_state.ps1")

$EmptyScript = Join-Path $PSScriptRoot "fuzzer\build_empty_apworld.ps1"
$CanaryScript = Join-Path $PSScriptRoot "fuzzer\build_canary_apworld.ps1"
$PassScript = Join-Path $PSScriptRoot "fuzzer\run_fuzz_pass.ps1"
$VenvPython = Join-Path $KdamgRoot ".py-env\venv\Scripts\python.exe"
$FuzzerStaging = Join-Path $KdamgFuzzerDir "upstream-staging"
$FuzzerUrl = "https://github.com/ionium-ap/Archipelago-fuzzer"
$RunsRoot = Join-Path $KdamgFuzzerDir "runs"

# fuzzer\ holds the upstream fuzzer next to a few things of this repository's own. A refresh
# replaces everything else and leaves these alone.
$KeepInFuzzer = @("khimera_damg.yaml", "empty-apworld", "runs", "upstream-staging")

$CountedChecks = @(
    "gerpocalypse",
    "indirect_conditions",
    "item_location_count",
    "detect_rule_variable_capture_issues",
    "check_placement_item_location_references",
    "detect_output_placement_changes"
)
$SinglePasses = @("rate") + $CountedChecks + @("determinism")

# The canary runs these two passes and expects both to fail: a plain generation must catch its
# unbeatable seed, and the item_location_count hook its short pool.
$CanaryPasses = @("rate", "item_location_count")

function Get-Commit {
    param([string] $Path)

    $sha = git -C $Path rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $sha) {
        return "unknown"
    }
    return $sha.Trim()
}

function Update-Fuzzer {
    # Clone next to the old copy and swap only once the clone succeeded, so a failed clone leaves
    # the previous fuzzer in place instead of nothing.
    New-Item -ItemType Directory -Path $KdamgFuzzerDir -Force | Out-Null
    if (Test-Path $FuzzerStaging) {
        Remove-Item $FuzzerStaging -Recurse -Force -ErrorAction Stop
    }
    git clone --depth 1 $FuzzerUrl $FuzzerStaging | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "git clone of $FuzzerUrl failed. The previous copy in $KdamgFuzzerDir is untouched."
    }
    $commit = (git -C $FuzzerStaging rev-parse HEAD).Trim()

    # A nested .git would make the outer repo treat fuzzer\ as an opaque boundary, and the
    # khimera_damg.yaml tracked there could not be committed. The commit is kept in a file instead.
    Remove-Item (Join-Path $FuzzerStaging ".git") -Recurse -Force -ErrorAction Stop

    $upstream = @(Get-ChildItem $FuzzerStaging -Force)
    foreach ($entry in $upstream) {
        if ($KeepInFuzzer -contains $entry.Name) {
            throw ("The fuzzer now ships $($entry.Name), which is a name this repository keeps in " +
                   "$KdamgFuzzerDir. The previous copy is untouched; the new clone is in $FuzzerStaging.")
        }
    }

    # Replace the upstream part wholesale, so a file removed upstream does not linger.
    foreach ($entry in @(Get-ChildItem $KdamgFuzzerDir -Force)) {
        if ($KeepInFuzzer -notcontains $entry.Name) {
            try {
                Remove-Item $entry.FullName -Recurse -Force -ErrorAction Stop
            }
            catch {
                throw ("Could not remove $($entry.FullName) ($($_.Exception.Message)). Something has it open, " +
                       "often a terminal whose working directory is inside it.")
            }
        }
    }
    foreach ($entry in $upstream) {
        Move-Item $entry.FullName $KdamgFuzzerDir -ErrorAction Stop
    }
    Remove-Item $FuzzerStaging -Recurse -Force -ErrorAction Stop

    # Everything in fuzzer\ is ignored except the fuzz-meta file, which is tracked.
    Set-Content -Path (Join-Path $KdamgFuzzerDir ".gitignore") -Value @("*", "!khimera_damg.yaml") -Encoding ascii
    Set-Content -Path (Join-Path $KdamgFuzzerDir "COMMIT") -Value $commit -Encoding ascii
    Write-Host "Fuzzer at $commit in $KdamgFuzzerDir"
}

function Invoke-Setup {
    # Never stand inside a folder this is about to replace: Windows refuses to delete a directory
    # that is any process's working directory.
    Push-Location $KdamgRoot
    try {
        $null = Assert-BuildState -Allowed @("development", "prepared") -Action "Setting up the fuzzer"
        if (-not (Test-Path $VenvPython)) {
            throw "The build venv was not found at $VenvPython. Run scripts\setup.ps1 first."
        }
        Update-Fuzzer
        Install-FuzzerFiles

        # empty-apworld is the 100-free-location world the index measures the failure rate with.
        # -Force clones it again, so a re-run picks up anything new upstream.
        & $EmptyScript -Force
    }
    finally {
        Pop-Location
    }
}

function Resolve-Passes {
    $requested = @($Pass)
    if ($requested.Count -eq 0) {
        $requested = @("rate")
    }

    $resolved = New-Object System.Collections.Generic.List[string]
    foreach ($name in $requested) {
        $expanded = switch ($name) {
            "all" { @("rate") + $CountedChecks }
            "checks" { $CountedChecks }
            default { @($name) }
        }
        foreach ($item in $expanded) {
            if ($item -ne "canary" -and $SinglePasses -notcontains $item) {
                throw "Unknown pass '$item'. Known: $($SinglePasses -join ', '), checks, all, canary."
            }
            if (-not $resolved.Contains($item)) {
                $resolved.Add($item)
            }
        }
    }
    return $resolved
}

# --- Setup ------------------------------------------------------------------------------------

if ($Setup) {
    try {
        Invoke-Setup
    }
    catch {
        Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    if (-not $Pass) {
        exit 0
    }
}

# --- Preflight --------------------------------------------------------------------------------

try {
    $Passes = Resolve-Passes
    if (-not (Test-Path $VenvPython)) {
        throw "The build venv was not found at $VenvPython. Run scripts\setup.ps1 first."
    }
    $Recorded = Assert-PreparedBuildCurrent -Action "Fuzzing"
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

$MetaPath = $null
if (-not $NoMeta) {
    if (-not (Test-Path $Meta)) {
        Write-Host "Fuzz-meta file not found at $Meta. Pass -NoMeta to run without one." -ForegroundColor Red
        exit 1
    }
    $MetaPath = (Resolve-Path $Meta).Path
}

# --- Passes -----------------------------------------------------------------------------------

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RunsRoot $Stamp
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

$FuzzerCommit = "unknown"
$CommitFile = Join-Path $KdamgFuzzerDir "COMMIT"
if (Test-Path $CommitFile) {
    $FuzzerCommit = (Get-Content $CommitFile -Raw).Trim()
}
$RunInfo = [ordered] @{
    started = (Get-Date).ToString("s")
    passes = @($Passes)
    runs = $Runs
    jobs = $Jobs
    yamls = $Yamls
    timeout = $Timeout
    meta = $MetaPath
    extra_args = @($ExtraArgs)
    apworld_sha256 = $Recorded.apworld_sha256
    source_fingerprint = $Recorded.source_fingerprint
    prepared_at = $Recorded.prepared_at
    repository_commit = Get-Commit $KdamgRoot
    archipelago_commit = Get-Commit $KdamgApRoot
    fuzzer_commit = $FuzzerCommit
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $RunDir "run.json"), ($RunInfo | ConvertTo-Json -Depth 4), $Utf8NoBom)

$Common = @{
    ArchiveDir = $RunDir
    Jobs = $Jobs
    Yamls = $Yamls
    Timeout = $Timeout
    ExtraArgs = $ExtraArgs
}

$Labels = New-Object System.Collections.Generic.List[string]
foreach ($name in $Passes) {
    if ($name -ne "canary") {
        $passMeta = ""
        if ($MetaPath) {
            $passMeta = $MetaPath
        }
        & $PassScript -Pass $name -Label $name -Runs $Runs -Meta $passMeta @Common
        $Labels.Add($name)
        continue
    }

    try {
        & $CanaryScript
    }
    catch {
        Write-Host "Building the canary failed: $($_.Exception.Message)" -ForegroundColor Red
        $Labels.Add("canary-build")
        continue
    }
    try {
        foreach ($canaryPass in $CanaryPasses) {
            $label = "canary-$canaryPass"
            & $PassScript -Pass $canaryPass -Label $label -Game "kdamg_canary" -Runs ([Math]::Min($Runs, 50)) `
                -ExpectFailures @Common
            $Labels.Add($label)
        }
    }
    finally {
        & $CanaryScript -Remove
    }
}

# --- Summary ----------------------------------------------------------------------------------

$Rows = @()
$AllOk = $true
foreach ($label in $Labels) {
    $resultPath = Join-Path (Join-Path $RunDir $label) "result.json"
    if (-not (Test-Path $resultPath)) {
        $Rows += [pscustomobject] [ordered] @{
            Pass = $label; Verdict = "error"; Total = ""; Failed = ""; Timeout = ""; Ignored = ""; Unfinished = ""
            Rate = "no result.json"
        }
        $AllOk = $false
        continue
    }
    $result = Get-Content $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($result.verdict -ne "ok") {
        $AllOk = $false
    }

    $rate = "n/a (check)"
    if ($result.kind -eq "rate") {
        if ($null -ne $result.rate) {
            $rate = "{0:P2}" -f [double] $result.rate
        }
        else {
            $rate = "none"
        }
    }
    if ($result.expect_failures) {
        $rate = "n/a (canary)"
    }

    $s = $result.stats
    $row = [ordered] @{
        Pass = $label; Verdict = $result.verdict; Total = ""; Failed = ""; Timeout = ""; Ignored = ""; Unfinished = ""
    }
    if ($null -ne $s) {
        $row.Total = $s.total
        $row.Failed = $s.failure
        $row.Timeout = $s.timeout
        $row.Ignored = $s.ignored
        $row.Unfinished = $s.unfinished
    }
    $row.Rate = $rate
    $Rows += [pscustomobject] $row
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$Rows | Format-Table -AutoSize | Out-String -Width 200 | Write-Host

foreach ($label in $Labels) {
    $resultPath = Join-Path (Join-Path $RunDir $label) "result.json"
    if (-not (Test-Path $resultPath)) {
        continue
    }
    $result = Get-Content $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $notes = @($result.notes)
    $errors = @($result.errors)
    if ($notes.Count -eq 0 -and ($errors.Count -eq 0 -or $result.expect_failures)) {
        continue
    }
    Write-Host "[$label]" -ForegroundColor Yellow
    foreach ($note in $notes) {
        Write-Host "  $note"
    }
    if (-not $result.expect_failures) {
        foreach ($entry in $errors) {
            $message = ($entry.message -replace "\s+", " ").Trim()
            if ($message.Length -gt 160) {
                $message = $message.Substring(0, 157) + "..."
            }
            Write-Host ("  {0,4}x  {1}" -f $entry.count, $message)
        }
    }
}

Write-Host ""
Write-Host "Archived to $RunDir"
if ($AllOk) {
    Write-Host "All passes ok." -ForegroundColor Green
    exit 0
}
Write-Host "At least one pass did not come back ok." -ForegroundColor Red
exit 1
