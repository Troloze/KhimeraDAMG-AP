# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
#
# PreToolUse guard for the landmark-review skill. Claude Code passes the pending tool call as JSON
# on stdin. Exit code 2 blocks the call and shows stderr to the model; exit code 0 lets it through.
#
# This is a guardrail against accidental writes during a review, not a sandbox. File tools are
# checked by path; shell commands are checked against a list of state-changing patterns.

$ErrorActionPreference = "Stop"

function Block([string]$reason) {
    [Console]::Error.WriteLine("landmark-review guard: $reason")
    exit 2
}

try {
    $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
} catch {
    Block "could not parse the hook input, so the call is blocked to be safe."
}

$tool = $payload.tool_name
$toolInput = $payload.tool_input

$projectDir = $env:CLAUDE_PROJECT_DIR
if (-not $projectDir) { $projectDir = $payload.cwd }
$projectDir = [System.IO.Path]::GetFullPath($projectDir).TrimEnd("\")
$reportDir = Join-Path $projectDir "docs\report"
$tempDir = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\")

function Test-Under([string]$path, [string]$root) {
    return $path.StartsWith("$root\", [System.StringComparison]::OrdinalIgnoreCase)
}

if ($tool -in @("Edit", "Write", "NotebookEdit")) {
    $target = $toolInput.file_path
    if (-not $target) { $target = $toolInput.notebook_path }
    if (-not $target) { Block "$tool call has no target path." }
    if (-not [System.IO.Path]::IsPathRooted($target)) { $target = Join-Path $projectDir $target }
    $target = [System.IO.Path]::GetFullPath($target)

    if (Test-Under $target $tempDir) { exit 0 }

    if (Test-Under $target $reportDir) {
        if ([System.IO.Path]::GetExtension($target) -ne ".md") {
            Block "only Markdown files may be written to docs/report/."
        }
        if ($tool -eq "Write" -and (Test-Path -LiteralPath $target)) {
            Block "$target already exists; earlier reports are never overwritten. Use a _2, _3 suffix."
        }
        exit 0
    }

    Block "$tool to $target is outside docs/report/ and the temp folder; the review may not write there."
}

if ($tool -in @("Bash", "PowerShell")) {
    $command = [string]$toolInput.command

    $denied = [ordered]@{
        "(?i)(^|\s)--?fix\b"                    = "ruff fixes are writes"
        "(?i)\bgit\s+(add|commit|checkout|switch|restore|stash|reset|clean|rm|mv|push|pull|fetch|merge|rebase|cherry-pick|revert|tag|am|apply|submodule)\b" = "git state changes are not permitted"
        "(?i)\b(Remove-Item|Move-Item|Rename-Item|Copy-Item|New-Item|Set-Content|Add-Content|Clear-Content|Out-File|Expand-Archive|Compress-Archive)\b" = "file-modifying cmdlets are not permitted"
        "(?i)(^|[\s;&|(])(rm|mv|cp|touch|mkdir|rmdir|del|ren|tee|truncate)\s" = "file-modifying commands are not permitted"
        "(?i)\bsed\s+(-[a-z]*i|--in-place)"     = "in-place edits are not permitted"
        "(?<![0-9])>{1,2}(?!\s*(&|\`$null|/dev/null|NUL\b))" = "output redirection to a file is not permitted"
    }

    foreach ($pattern in $denied.Keys) {
        if ($command -match $pattern) {
            Block "$($denied[$pattern]). Command: $command"
        }
    }
    exit 0
}

exit 0
