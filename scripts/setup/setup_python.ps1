# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

param(
    [string] $Version = "3.11.9",
    [switch] $Force
)

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$EnvDir = Join-Path $Root ".py-env"
$PythonDir = Join-Path $EnvDir "python"
$PythonExe = Join-Path $PythonDir "python.exe"
$Staging = Join-Path $EnvDir "python-staging"

if ((Test-Path $PythonExe) -and (-not $Force)) {
    Write-Host "Python already set up at $PythonExe"
    exit 0
}

# Python comes from the official NuGet package, not the python.org installer. The installer
# registers a per-user install with Windows, and uninstalling one that lives on any drive but C:
# fails with Error 1926 on <drive>:\Config.Msi, because a per-user uninstall runs unelevated. The
# NuGet package is the same CPython build as a plain zip, meant for build systems without a
# system-wide Python: nothing is registered, so removing it is deleting the folder. It leaves out
# tkinter, IDLE and the docs, which nothing here uses; venv and a bundled pip are included.
$PackageUrl = "https://api.nuget.org/v3-flatcontainer/python/$Version/python.$Version.nupkg"

# Staged inside .py-env rather than TEMP, because the swap at the end is a rename and a rename
# cannot cross drives. The previous interpreter stays in place until the new one is unpacked.
if (Test-Path $Staging) {
    Remove-Item $Staging -Recurse -Force
}
New-Item -ItemType Directory -Path $Staging -Force | Out-Null
$PackagePath = Join-Path $Staging "python.$Version.zip"
$Extracted = Join-Path $Staging "package"

try {
    # Windows PowerShell 5.1 does not always offer TLS 1.2, and nuget.org requires it.
    [System.Net.ServicePointManager]::SecurityProtocol =
        [System.Net.ServicePointManager]::SecurityProtocol -bor [System.Net.SecurityProtocolType]::Tls12
    $ProgressPreference = "SilentlyContinue"
    try {
        Invoke-WebRequest -Uri $PackageUrl -OutFile $PackagePath -UseBasicParsing -ErrorAction Stop
    }
    catch {
        throw "Could not download Python $Version from $PackageUrl. $($_.Exception.Message)"
    }

    # ZipFile rather than Expand-Archive: it takes seconds instead of minutes for ~1300 files, and
    # Expand-Archive on 5.1 refuses a .nupkg name anyway.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($PackagePath, $Extracted)

    # The package keeps the interpreter under tools\; the rest is NuGet metadata.
    $Tools = Join-Path $Extracted "tools"
    if (-not (Test-Path (Join-Path $Tools "python.exe"))) {
        throw "The NuGet package for Python $Version has no tools\python.exe."
    }

    if (Test-Path $PythonDir) {
        try {
            Remove-Item $PythonDir -Recurse -Force -ErrorAction Stop
        }
        catch {
            throw ("Could not delete the old $PythonDir ($($_.Exception.Message)). Something has it open, " +
                   "often a running python.exe from it or from .py-env\venv.")
        }
    }
    Move-Item $Tools $PythonDir -ErrorAction Stop
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
finally {
    Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue
}

$Reported = & $PythonExe -c "import platform; print(platform.python_version())"
if ($LASTEXITCODE -ne 0 -or $Reported -ne $Version) {
    Write-Error "$PythonExe does not run as Python $Version (it reported '$Reported')."
    exit 1
}

Write-Host "Python $Version unpacked at $PythonExe"
exit 0
