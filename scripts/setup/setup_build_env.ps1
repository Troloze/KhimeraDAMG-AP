# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [string] $PythonExe = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "python\python.exe"),
    [switch] $Force
)

$Root         = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Venv         = Join-Path $Root "py-env"
$VenvPython   = Join-Path $Venv "Scripts\python.exe"
$ApRoot       = Join-Path $Root "Archipelago"
$ModuleUpdate = Join-Path $ApRoot "ModuleUpdate.py"

if ((Test-Path $VenvPython) -and (-not $Force)) {
    Write-Host "Build environment already set up at $VenvPython"
    exit 0
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "No base interpreter at $PythonExe. Run scripts\setup\setup_python.ps1 first."
    exit 1
}
if (-not (Test-Path $ModuleUpdate)) {
    Write-Error "Archipelago submodule not checked out: $ModuleUpdate is missing."
    exit 1
}

# ModuleUpdate.py hard-raises on anything outside 3.11.9 - 3.13.x on Windows, so a venv built
# from an out-of-range interpreter would fail on every import rather than here at setup time.
$BaseVersion = [version](& $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
if ($BaseVersion -lt [version]"3.11.9" -or $BaseVersion -ge [version]"3.14.0") {
    Write-Error "Archipelago supports Python 3.11.9 through 3.13.x; $PythonExe is $BaseVersion."
    exit 1
}

# requirements.txt pulls kivymd, and worlds/zillion pulls zilliandomizer, straight from GitHub.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git was not found on PATH. ModuleUpdate installs kivymd and zilliandomizer from git."
    exit 1
}

if (Test-Path $Venv) {
    Remove-Item $Venv -Recurse -Force
}

Write-Host "Creating venv at $Venv from Python $BaseVersion"
& $PythonExe -m venv $Venv

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv creation did not produce $VenvPython"
    exit 1
}

# Self-ignore the way python/ and fuzzer/ do, so the repo root .gitignore needs no entry.
$GitignorePath = Join-Path $Venv ".gitignore"
if (-not (Test-Path $GitignorePath)) {
    Set-Content -Path $GitignorePath -Value "*" -Encoding utf8
}

# ModuleUpdate.py is Archipelago's own installer. It resolves requirements.txt plus every
# worlds/*/requirements.txt, installing each against requirements.txt as a constraint file,
# which is what keeps the hash-pinned (pyevermizer) and git-sourced (kivymd, zilliandomizer)
# entries resolvable. -y answers its install prompts, -f skips the "already satisfied" probe.
# It looks for each requirements file relative to argv[0] before its own location, so it has
# to run from the Archipelago root.
Write-Host "Installing Archipelago requirements (this downloads a few hundred MB)..."
Push-Location $ApRoot
try {
    & $VenvPython $ModuleUpdate -y -f
} finally {
    Pop-Location
}

# Smoke-test the imports an apworld build actually performs.
$Probe = "import pathspec, yaml, schema, jinja2, orjson, platformdirs, bsdiff4, websockets; " +
         "import pkg_resources; print('ok')"
$Result = & $VenvPython -c $Probe
if ($Result -ne "ok") {
    Write-Error "Requirement install finished but the build environment is incomplete."
    exit 1
}

Write-Host "Build environment ready at $VenvPython"
