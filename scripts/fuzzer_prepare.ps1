# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

<#
.SYNOPSIS
    Builds the apworld and puts Archipelago\ in the prepared state the fuzzer and the full core
    suite run in.

.DESCRIPTION
    From the development state, this:

      1. builds the apworld through scripts\build_apworld.ps1, which needs the world link;
      2. copies fuzz.py and hooks\ from fuzzer\ into the Archipelago root, and builds
         custom_worlds\empty.apworld if it is missing;
      3. removes the world link at Archipelago\worlds\khimera_damg and installs the built apworld
         in Archipelago\custom_worlds;
      4. writes Archipelago\kdamg_prepared.json, recording the apworld's hash and a fingerprint of
         khimera_damg\, so the runners can refuse a build that no longer matches the source.

    The link has to go because Archipelago loads world folders first and skips an .apworld whose
    game is already loaded: with the link in place, the source would be tested, not the build.

    When Archipelago\ is already prepared, it is cleaned up first and prepared again with a fresh
    build. In any other state the script stops and points at scripts\restore_archipelago.ps1.

    scripts\fuzzer_cleanup.ps1 returns to the development state. Until then, building and
    scripts\run_tests.ps1 refuse to run, since both need the link.

    Needs the fuzzer to be set up (scripts\run_fuzzer.ps1 -Setup).
#>

. (Join-Path $PSScriptRoot "build\build_state.ps1")

$BuildScript = Join-Path $PSScriptRoot "build_apworld.ps1"
$CleanupScript = Join-Path $PSScriptRoot "fuzzer_cleanup.ps1"
$EmptyScript = Join-Path $PSScriptRoot "fuzzer\build_empty_apworld.ps1"

try {
    $State = Assert-BuildState -Allowed @("development", "prepared") -Action "Preparing for the fuzzer"
    if ($State.Name -eq "prepared") {
        Write-Host "Archipelago\ is already prepared; cleaning up and preparing again with a fresh build."
        & $CleanupScript
        if ($LASTEXITCODE -ne 0) {
            throw "scripts\fuzzer_cleanup.ps1 failed, so the prepared state could not be rebuilt."
        }
    }
    if (-not (Test-Path (Join-Path $KdamgFuzzerDir "fuzz.py"))) {
        throw "The fuzzer is not set up in $KdamgFuzzerDir. Run scripts\run_fuzzer.ps1 -Setup first."
    }

    # 1. Build, through the link. build_apworld.ps1 throws when it fails.
    $Started = Get-Date
    & $BuildScript
    if (-not (Test-Path $KdamgBuiltApWorld) -or (Get-Item $KdamgBuiltApWorld).LastWriteTime -lt $Started) {
        throw "scripts\build_apworld.ps1 did not produce a fresh $KdamgBuiltApWorld."
    }
    # After the build, which regenerates the patch tables inside khimera_damg\.
    $Fingerprint = Get-SourceFingerprint

    # 2. The fuzzer's files. Neither touches the state, so they go in while the link is still there.
    Install-FuzzerFiles
    if (-not (Test-Path $KdamgEmptyApWorld)) {
        & $EmptyScript
    }

    # 3. Swap the link for the build. DirectoryInfo.Delete() removes the link itself; Remove-Item
    # on Windows PowerShell can recurse into the junction's target, which is khimera_damg\.
    (Get-Item $KdamgWorldLink -Force).Delete()
    New-Item -ItemType Directory -Path $KdamgCustomWorlds -Force | Out-Null
    Copy-Item $KdamgBuiltApWorld $KdamgInstalledApWorld -Force -ErrorAction Stop

    # 4. Record what was installed.
    $Recorded = [ordered] @{
        prepared_at = (Get-Date).ToString("s")
        apworld_sha256 = (Get-FileHash $KdamgInstalledApWorld -Algorithm SHA256).Hash
        source_fingerprint = $Fingerprint
        archipelago_commit = (git -C $KdamgApRoot rev-parse HEAD).Trim()
    }
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($KdamgStateFile, ($Recorded | ConvertTo-Json), $Utf8NoBom)

    $null = Assert-BuildState -Allowed @("prepared") -Action "Preparing for the fuzzer"
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "Archipelago\ is prepared: $KdamgInstalledApWorld is installed and the world link is removed."
Write-Host "Run scripts\fuzzer_cleanup.ps1 when done fuzzing."
exit 0
