# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Runs Eijebong's fuzzer (ionium-ap/Archipelago-fuzzer) against the apworld, one pass at a time.

.DESCRIPTION
    Moves the fuzzer worktree at fuzz-env\ap-fuzz to the commit the Archipelago submodule is at,
    if it is anywhere else, builds the apworld fresh, installs it into the worktree, and runs the
    requested passes through scripts\fuzzer\run_fuzz_pass.ps1. Every pass is archived under
    fuzz-env\ap-fuzz\fuzz_runs\<timestamp>\<pass>\ with its command line, fuzz.py's own output and
    a result.json. A summary table follows the last pass.

    Why passes: each checking hook turns every outcome it is not testing into a success or an
    OptionError, so a run with several hooks loaded cannot report a failure at all. The failure
    rate the index cares about comes from the "rate" pass alone, which loads no checking hook and
    puts the Empty world in every generation. See docs\Running the Fuzzer.md.

    Exit code: 0 when every pass came back "ok", 1 otherwise.

.PARAMETER Setup
    Create the fuzzer worktree if needed (or move it to the submodule's commit), refresh the
    fuzzer clone in \fuzzer and copy it into the worktree, create the venv if needed, and rebuild
    empty.apworld. Then stop, unless -Pass is also given.

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
    The fuzz-meta file. Defaults to fuzz-meta\khimera_damg.yaml, resolved to an absolute path
    because fuzz.py runs from the worktree.

.PARAMETER NoMeta
    Do not pass a fuzz-meta file.

.PARAMETER SkipBuild
    Reuse the apworld already in the worktree's custom_worlds instead of building one.

.PARAMETER ExtraArgs
    Extra arguments for fuzz.py, added to every pass. --hook is refused: pick a pass instead.

.EXAMPLE
    scripts/run_fuzzer.ps1 -Setup
    scripts/run_fuzzer.ps1
    scripts/run_fuzzer.ps1 -Pass checks -Runs 200
    scripts/run_fuzzer.ps1 -Pass all
    scripts/run_fuzzer.ps1 -Pass canary
#>

param(
    [switch] $Setup,
    [string[]] $Pass,
    [int] $Runs = 500,
    [int] $Jobs = 16,
    [string] $Yamls = "1",
    [int] $Timeout = 15,
    [string] $Meta = (Join-Path (Split-Path $PSScriptRoot -Parent) "fuzz-meta\khimera_damg.yaml"),
    [switch] $NoMeta,
    [switch] $SkipBuild,
    [string[]] $ExtraArgs = @(),
    [string] $PythonExe = (Join-Path (Split-Path $PSScriptRoot -Parent) "python\python.exe")
)

$Root = Split-Path $PSScriptRoot -Parent
$ApRoot = Join-Path $Root "Archipelago"
$BuildScript = Join-Path $PSScriptRoot "build_apworld.ps1"
$EmptyScript = Join-Path $PSScriptRoot "fuzzer\build_empty_apworld.ps1"
$CanaryScript = Join-Path $PSScriptRoot "fuzzer\build_canary_apworld.ps1"
$PassScript = Join-Path $PSScriptRoot "fuzzer\run_fuzz_pass.ps1"
$BuiltApWorld = Join-Path $Root "build\apworlds\khimera_damg.apworld"
$FuzzEnv = Join-Path $Root "fuzz-env"
$FuzzRoot = Join-Path $FuzzEnv "ap-fuzz"
$FuzzerRepo = Join-Path $Root "fuzzer"
$FuzzerStaging = Join-Path $FuzzEnv "fuzzer-clone"
$FuzzerUrl = "https://github.com/ionium-ap/Archipelago-fuzzer"
$CustomWorldsDir = Join-Path $FuzzRoot "custom_worlds"
$ApWorldPath = Join-Path $CustomWorldsDir "khimera_damg.apworld"
$Venv = Join-Path $FuzzRoot ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$RunsRoot = Join-Path $FuzzRoot "fuzz_runs"

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

function Sync-FuzzWorktree {
    # Puts the fuzzer worktree on the commit the Archipelago submodule has checked out, creating
    # the worktree if there is none. The apworld is built against the submodule, so fuzzing it on
    # any other core measures something else. Both share the submodule's object store, so the
    # commit is always available locally and nothing is fetched.
    #
    # Returns $true when the worktree was created or moved, so the caller knows the venv and
    # empty.apworld may no longer match it. Native output goes to Out-Host so that it does not
    # become part of the return value.
    $target = Get-Commit $ApRoot
    if ($target -eq "unknown") {
        throw "Could not read the Archipelago submodule's commit. Run git submodule update --init first."
    }

    if (-not (Test-Path $FuzzRoot)) {
        New-Item -ItemType Directory -Path $FuzzEnv -Force | Out-Null
        git -C $ApRoot worktree add --detach $FuzzRoot $target | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "git worktree add failed for $FuzzRoot."
        }
        Write-Host "Created the fuzzer worktree at $target"
        return $true
    }

    $current = Get-Commit $FuzzRoot
    if ($current -eq "unknown") {
        throw "$FuzzRoot exists but is not a git worktree. Move it out of the way and run -Setup."
    }
    if ($current -eq $target) {
        return $false
    }

    # Only changes to tracked files can be lost or block the checkout. Everything the fuzzer adds
    # (fuzz.py, hooks, the venv, custom_worlds, fuzz_runs) is untracked and stays where it is.
    $dirty = git -C $FuzzRoot status --porcelain --untracked-files=no
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed in $FuzzRoot."
    }
    if ($dirty) {
        throw ("The fuzzer worktree has changes to tracked files, so it was not moved to ${target}:`n" +
               ($dirty -join "`n"))
    }

    Write-Host "Moving the fuzzer worktree from $current to $target, the commit the Archipelago submodule is at."
    git -C $FuzzRoot checkout --quiet --detach $target | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "git checkout of $target in $FuzzRoot failed."
    }
    return $true
}

function Install-FuzzRequirements {
    & $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $FuzzRoot "requirements.txt") | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Installing the worktree's requirements into $Venv failed."
    }
}

function Invoke-Setup {
    # Never stand inside a folder this is about to replace: Windows refuses to delete a directory
    # that is any process's working directory, and the old script then carried on regardless.
    Push-Location $Root
    try {
        $moved = Sync-FuzzWorktree

        # Clone next to the old copy and swap only once the clone succeeded, so a failed clone
        # leaves the previous fuzzer in place instead of nothing.
        if (Test-Path $FuzzerStaging) {
            Remove-Item $FuzzerStaging -Recurse -Force -ErrorAction Stop
        }
        git clone --depth 1 $FuzzerUrl $FuzzerStaging
        if ($LASTEXITCODE -ne 0) {
            throw "git clone of $FuzzerUrl failed. The previous copy in $FuzzerRepo is untouched."
        }
        $commit = (git -C $FuzzerStaging rev-parse HEAD).Trim()

        # A nested .git makes the outer repo treat this whole directory as an opaque boundary,
        # so its own .gitignore below would never be consulted. Strip it so /fuzzer behaves like
        # a plain self-ignoring folder, the same as /python. The commit is kept in a file instead.
        Remove-Item (Join-Path $FuzzerStaging ".git") -Recurse -Force -ErrorAction Stop
        Set-Content -Path (Join-Path $FuzzerStaging ".gitignore") -Value "*" -Encoding ascii
        Set-Content -Path (Join-Path $FuzzerStaging "COMMIT") -Value $commit -Encoding ascii

        if (Test-Path $FuzzerRepo) {
            try {
                Remove-Item $FuzzerRepo -Recurse -Force -ErrorAction Stop
            }
            catch {
                throw ("Could not remove the old $FuzzerRepo ($($_.Exception.Message)). Something has it open, " +
                       "often a terminal whose working directory is inside it. The new clone is in $FuzzerStaging.")
            }
        }
        Move-Item $FuzzerStaging $FuzzerRepo -ErrorAction Stop

        # Replace the hooks folder rather than copying over it, so a hook removed upstream does
        # not linger in the worktree.
        $worktreeHooks = Join-Path $FuzzRoot "hooks"
        if (Test-Path $worktreeHooks) {
            Remove-Item $worktreeHooks -Recurse -Force -ErrorAction Stop
        }
        Copy-Item (Join-Path $FuzzerRepo "fuzz.py") $FuzzRoot -Force -ErrorAction Stop
        Copy-Item (Join-Path $FuzzerRepo "hooks") $worktreeHooks -Recurse -ErrorAction Stop
        Write-Host "Fuzzer at $commit copied into $FuzzRoot"

        if (-not (Test-Path $VenvPython)) {
            if (-not (Test-Path $PythonExe)) {
                throw "Python not found at $PythonExe. Run scripts\setup.ps1 first."
            }
            & $PythonExe -m venv $Venv
            if ($LASTEXITCODE -ne 0) {
                throw "Creating the venv at $Venv failed."
            }
            Install-FuzzRequirements
        }
        elseif ($moved) {
            Install-FuzzRequirements
        }

        # empty-apworld is the 100-free-location world the index measures the failure rate with.
        # -Force re-clones it, so a re-run picks up anything new upstream. It runs last because it
        # verifies the artifact through the venv created just above.
        & $EmptyScript -Force
    }
    finally {
        Pop-Location
    }
}

function Install-ApWorld {
    if (-not (Test-Path $CustomWorldsDir)) {
        New-Item -ItemType Directory -Path $CustomWorldsDir | Out-Null
    }

    if ($SkipBuild) {
        if (-not (Test-Path $ApWorldPath)) {
            throw "-SkipBuild was given, but there is no apworld at $ApWorldPath to reuse."
        }
        $age = (Get-Item $ApWorldPath).LastWriteTime
        Write-Warning "Reusing the apworld installed at $age; changes made since then are not being fuzzed."
        return
    }

    # A directory link works for static analysis but not for the fuzzer: only .apworld zips in
    # custom_worlds get registered, through a dedicated meta-path finder. It has to come from the
    # build component, not a hand-made zip, which would lack version/compatible_version in its
    # manifest and load with no metadata at all.
    if (Test-Path $ApWorldPath) {
        Remove-Item $ApWorldPath -Force
    }
    $started = Get-Date
    & $BuildScript
    if ($LASTEXITCODE -ne 0) {
        throw "scripts\build_apworld.ps1 failed with exit code $LASTEXITCODE."
    }
    if (-not (Test-Path $BuiltApWorld) -or (Get-Item $BuiltApWorld).LastWriteTime -lt $started) {
        throw "scripts\build_apworld.ps1 did not produce a fresh $BuiltApWorld."
    }
    Copy-Item $BuiltApWorld $ApWorldPath -Force -ErrorAction Stop
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
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPython) -or -not (Test-Path (Join-Path $FuzzRoot "fuzz.py"))) {
    Write-Host "Fuzzer environment not found at $FuzzRoot. Run with -Setup first." -ForegroundColor Red
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

try {
    # -Setup has just synced and refreshed everything itself.
    if (-not $Setup -and (Sync-FuzzWorktree)) {
        # A different core can need other packages, and a different container_version makes the
        # existing empty.apworld unloadable. The empty-apworld clone itself is reused.
        Push-Location $Root
        try {
            Install-FuzzRequirements
            & $EmptyScript
        }
        finally {
            Pop-Location
        }
    }
}
catch {
    Write-Host "Could not bring the fuzzer worktree in line with the submodule: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
$WorktreeCommit = Get-Commit $FuzzRoot

try {
    Install-ApWorld
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# --- Passes -----------------------------------------------------------------------------------

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RunsRoot $Stamp
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

$FuzzerCommit = "unknown"
$CommitFile = Join-Path $FuzzerRepo "COMMIT"
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
    apworld_sha256 = (Get-FileHash $ApWorldPath -Algorithm SHA256).Hash
    repository_commit = Get-Commit $Root
    worktree_commit = $WorktreeCommit
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
