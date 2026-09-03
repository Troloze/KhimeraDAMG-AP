# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [string] $Version = "3.13.15",
    [switch] $Force
)

$Root = Split-Path $PSScriptRoot -Parent
$PythonDir = Join-Path $Root "python"
$PythonExe = Join-Path $PythonDir "python.exe"

if ((Test-Path $PythonExe) -and (-not $Force)) {
    Write-Host "Python already set up at $PythonExe"
    exit 0
}

$InstallerUrl = "https://www.python.org/ftp/python/$Version/python-$Version-amd64.exe"
$InstallerPath = Join-Path $env:TEMP "python-$Version-amd64.exe"

$ProgressPreference = "SilentlyContinue"
Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath

if (Test-Path $PythonDir) {
    Remove-Item $PythonDir -Recurse -Force
}

# Per-user install into a custom TargetDir needs no admin elevation. PrependPath/AppendPath
# stay off so this interpreter never touches the system PATH; it's only ever invoked by its
# full path from run_fuzzer.ps1.
$InstallArgs = @(
    "/quiet",
    "InstallAllUsers=0",
    "TargetDir=`"$PythonDir`"",
    "PrependPath=0",
    "AppendPath=0",
    "Shortcuts=0",
    "AssociateFiles=0",
    "Include_launcher=0",
    "InstallLauncherAllUsers=0",
    "Include_test=0",
    "Include_pip=1",
    "CompileAll=0"
)

Start-Process -FilePath $InstallerPath -ArgumentList $InstallArgs -Wait -NoNewWindow
Remove-Item $InstallerPath -Force

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python install did not produce $PythonExe"
    exit 1
}

$GitignorePath = Join-Path $PythonDir ".gitignore"
if (-not (Test-Path $GitignorePath)) {
    Set-Content -Path $GitignorePath -Value "*" -Encoding utf8
}

Write-Host "Python $Version installed at $PythonExe"
