# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

# The state Archipelago\ is in with respect to this apworld, shared by every script that builds,
# tests or fuzzes. Dot-source it; it defines variables prefixed Kdamg and a few functions, which
# report failure by throwing.
#
#   development  The world link at Archipelago\worlds\khimera_damg points at khimera_damg\, and
#                the built apworld is not installed. Building, the apworld's own tests and the
#                scoped core suite need this state. scripts\fuzzer_cleanup.ps1 returns to it.
#   prepared     The world link is absent, the built apworld is installed in
#                Archipelago\custom_worlds next to empty.apworld, fuzz.py and hooks\ sit in the
#                Archipelago root, and kdamg_prepared.json records what was built. The fuzzer and
#                the full core suite need this state. scripts\fuzzer_prepare.ps1 enters it.
#   ambiguous    Anything else, for instance a run that was killed half-way. Nothing guesses its
#                way out of it: scripts\restore_archipelago.ps1 resets Archipelago\ instead.
#   missing      Archipelago\ is not set up.
#
# The two usable states exist because of how Archipelago loads worlds: folders in worlds\ come
# first, and an .apworld whose game is already loaded is skipped with only a warning. With the
# link in place, the built apworld would never be the one loaded.

$KdamgRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$KdamgApRoot = Join-Path $KdamgRoot "Archipelago"
# The clone's git directory lives outside it (see Get-CloneGitDir in scripts\setup\repository.ps1),
# so git has to be pointed at it: git -C Archipelago would find this repository's .git instead.
$KdamgApGitDir = Join-Path $KdamgRoot ".repos\Archipelago.git"
$KdamgWorldSource = Join-Path $KdamgRoot "khimera_damg"
$KdamgWorldLink = Join-Path $KdamgApRoot "worlds\khimera_damg"
$KdamgBuiltApWorld = Join-Path $KdamgApRoot "build\apworlds\khimera_damg.apworld"
$KdamgCustomWorlds = Join-Path $KdamgApRoot "custom_worlds"
$KdamgInstalledApWorld = Join-Path $KdamgCustomWorlds "khimera_damg.apworld"
$KdamgEmptyApWorld = Join-Path $KdamgCustomWorlds "empty.apworld"
$KdamgCanaryApWorld = Join-Path $KdamgCustomWorlds "kdamg_canary.apworld"
$KdamgStateFile = Join-Path $KdamgApRoot "kdamg_prepared.json"
$KdamgFuzzerDir = Join-Path $KdamgRoot "fuzzer"
$KdamgRestoreHint = ("Run scripts\restore_archipelago.ps1 to reset it: it recreates the world link and removes " +
                     "everything the build and the fuzzer added.")

function Get-BuildState {
    # Returns @{ Name = "development" | "prepared" | "ambiguous" | "missing"; Problems = [string[]] }.
    # Problems says why a state is ambiguous.
    if (-not (Test-Path (Join-Path $KdamgApRoot "worlds\Files.py"))) {
        return @{ Name = "missing"; Problems = @("Archipelago is not set up at $KdamgApRoot.") }
    }

    $problems = New-Object System.Collections.Generic.List[string]

    $linkState = "absent"
    $link = Get-Item $KdamgWorldLink -Force -ErrorAction SilentlyContinue
    if ($link) {
        if (-not $link.LinkType) {
            $linkState = "folder"
            $problems.Add("$KdamgWorldLink is a real folder, not the world link.")
        }
        else {
            $target = [System.IO.Path]::GetFullPath(@($link.Target)[0]).TrimEnd("\")
            if ($target -eq [System.IO.Path]::GetFullPath($KdamgWorldSource).TrimEnd("\")) {
                $linkState = "ok"
            }
            else {
                $linkState = "elsewhere"
                $problems.Add("The world link points at $target instead of $KdamgWorldSource.")
            }
        }
    }

    $installed = Test-Path $KdamgInstalledApWorld
    $marker = Test-Path $KdamgStateFile

    if ($linkState -eq "ok" -and -not $installed -and -not $marker) {
        return @{ Name = "development"; Problems = @() }
    }

    if ($linkState -eq "absent" -and $installed -and $marker) {
        foreach ($required in @(
            $KdamgEmptyApWorld,
            (Join-Path $KdamgApRoot "fuzz.py"),
            (Join-Path $KdamgApRoot "hooks")
        )) {
            if (-not (Test-Path $required)) {
                $problems.Add("The prepared state is missing $required.")
            }
        }
        try {
            $null = Get-Content $KdamgStateFile -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            $problems.Add("$KdamgStateFile cannot be read.")
        }
        if ($problems.Count -eq 0) {
            return @{ Name = "prepared"; Problems = @() }
        }
        return @{ Name = "ambiguous"; Problems = @($problems) }
    }

    if ($linkState -eq "absent") {
        $problems.Add("The world link at $KdamgWorldLink is missing.")
    }
    if ($installed -and $linkState -ne "absent") {
        $problems.Add("$KdamgInstalledApWorld is installed while $KdamgWorldLink exists, so it would not be loaded.")
    }
    if ($installed -and -not $marker) {
        $problems.Add("$KdamgInstalledApWorld is installed, but not by scripts\fuzzer_prepare.ps1 ($KdamgStateFile is missing).")
    }
    if ($marker -and -not $installed) {
        $problems.Add("$KdamgStateFile exists, but the apworld it describes is not installed.")
    }
    return @{ Name = "ambiguous"; Problems = @($problems) }
}

function Get-StateError {
    # The message for being in $State.Name when $Action needs one of $Allowed.
    param(
        [hashtable] $State,
        [string[]] $Allowed,
        [string] $Action
    )

    switch ($State.Name) {
        "missing" {
            return "$Action needs Archipelago, which is not set up at $KdamgApRoot. Run scripts\setup.ps1."
        }
        "ambiguous" {
            return ("$Action stopped: Archipelago\ is in neither the development nor the prepared state.`n  " +
                    ($State.Problems -join "`n  ") + "`n$KdamgRestoreHint")
        }
        "prepared" {
            return ("$Action needs the development state, but Archipelago\ is prepared for the fuzzer. " +
                    "Run scripts\fuzzer_cleanup.ps1 first.")
        }
        default {
            return ("$Action needs Archipelago\ prepared for the fuzzer, with the built apworld installed. " +
                    "Run scripts\fuzzer_prepare.ps1 first.")
        }
    }
}

function Assert-BuildState {
    # Throws unless Archipelago\ is in one of the $Allowed states. Returns the state.
    param(
        [string[]] $Allowed,
        [string] $Action
    )

    $state = Get-BuildState
    if ($Allowed -notcontains $state.Name) {
        throw (Get-StateError -State $state -Allowed $Allowed -Action $Action)
    }
    return $state
}

function Get-SourceFingerprint {
    # A hash over every file the apworld is built from: khimera_damg\ without its tests and
    # __pycache__ folders, which never reach the build. Compared against the one fuzzer_prepare.ps1
    # recorded, it tells whether the installed apworld is still current.
    $base = [System.IO.Path]::GetFullPath($KdamgWorldSource).TrimEnd("\") + "\"
    $lines = Get-ChildItem $KdamgWorldSource -Recurse -File -Force |
        ForEach-Object {
            $relative = $_.FullName.Substring($base.Length)
            if ($relative -like "tests\*" -or $relative -match '(^|\\)__pycache__\\') {
                return
            }
            "$relative`t$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)"
        } |
        Sort-Object

    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes)) -replace "-", "")
    }
    finally {
        $sha.Dispose()
    }
}

function Assert-PreparedBuildCurrent {
    # Throws unless Archipelago\ is prepared and its installed apworld is still the one built from
    # the current khimera_damg\. Returns the recorded state file's contents.
    param(
        [string] $Action
    )

    $null = Assert-BuildState -Allowed @("prepared") -Action $Action
    $recorded = Get-Content $KdamgStateFile -Raw | ConvertFrom-Json

    if ((Get-FileHash $KdamgInstalledApWorld -Algorithm SHA256).Hash -ne $recorded.apworld_sha256) {
        throw ("$Action stopped: the apworld installed in $KdamgCustomWorlds is not the one " +
               "scripts\fuzzer_prepare.ps1 built. Run scripts\fuzzer_prepare.ps1 again.")
    }
    if ((Get-SourceFingerprint) -ne $recorded.source_fingerprint) {
        throw ("$Action stopped: khimera_damg\ has changed since scripts\fuzzer_prepare.ps1 built the " +
               "installed apworld, so it would test an old build. Run scripts\fuzzer_prepare.ps1 again.")
    }
    return $recorded
}

function Install-FuzzerFiles {
    # fuzz.py puts its own folder on sys.path to import Archipelago, so it has to sit in the
    # Archipelago root, with the hooks it imports next to it. restore_archipelago.ps1 deletes the
    # copies along with everything else untracked.
    $fuzzPy = Join-Path $KdamgFuzzerDir "fuzz.py"
    if (-not (Test-Path $fuzzPy)) {
        throw "The fuzzer is not set up in $KdamgFuzzerDir. Run scripts\run_fuzzer.ps1 -Setup first."
    }
    Copy-Item $fuzzPy $KdamgApRoot -Force -ErrorAction Stop

    # Replace the hooks folder rather than copying over it, so a hook removed upstream does not
    # linger in Archipelago\.
    $apHooks = Join-Path $KdamgApRoot "hooks"
    if (Test-Path $apHooks) {
        Remove-Item $apHooks -Recurse -Force -ErrorAction Stop
    }
    Copy-Item (Join-Path $KdamgFuzzerDir "hooks") $apHooks -Recurse -ErrorAction Stop
}
