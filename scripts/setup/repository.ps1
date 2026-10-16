# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

# Helpers shared by the scripts that manage the two folders this repository downloads from GitHub
# instead of tracking: Archipelago\ and KhimeraDAMG-AP-Mod\. Dot-source it; it only defines
# functions, and they report failure by throwing.
#
# Each folder is a depth-1 clone, ignored by the root .gitignore and meant to be disposable:
# anything may write into it, and restore_<folder>.ps1 puts it back. The commit a folder was set
# up at is recorded inside the clone as refs/kdamg/pinned, which is what a restore returns to. The
# ref sits outside refs/heads and refs/tags so nothing done inside the clone moves it by accident.
#
# A clone's git directory is kept outside its folder, at .repos\<folder>.git in this repository
# (also ignored), so the folder holds no .git of its own. That keeps editors from treating it as a
# nested repository, and keeps git's read-only pack files out of it, so the folder can be deleted
# by hand without the "administrator permission" prompt those files cause in Explorer. With the
# git directory intact, a restore brings back a deleted folder without downloading anything.
#
# Every git call against a clone names both directories outright (Get-CloneGitArgs). Without a
# .git in the folder, git -C would otherwise discover this repository's and act on it instead.
# core.worktree is also set, relative to the git directory, so that git --git-dir=<it> works by
# hand from anywhere.

$PinnedRef = "refs/kdamg/pinned"

function Get-CloneGitDir {
    # The git directory of the clone at $Path: .repos\<folder>.git next to the folder.
    param(
        [string] $Path
    )

    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    return Join-Path (Split-Path $full -Parent) ".repos\$(Split-Path $full -Leaf).git"
}

function Get-CloneGitArgs {
    # The git options that point a command at the clone at $Path and its git directory.
    param(
        [string] $Path
    )

    return @("--git-dir=$(Get-CloneGitDir $Path)", "--work-tree=$([System.IO.Path]::GetFullPath($Path))")
}

function Invoke-Git {
    # Runs git and throws $Failure on a non-zero exit. Output goes to the host so that it never
    # becomes part of a caller's return value.
    param(
        [string[]] $Arguments,
        [string] $Failure
    )

    & git @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw $Failure
    }
}

function Get-TagCommit {
    # Finds a tag in git ls-remote --tags output and returns the commit it points at, or $null.
    # An annotated tag is listed twice, the second time suffixed ^{} with the commit it peels to,
    # and that one wins.
    param(
        [string[]] $Lines,
        [string] $Name
    )

    $commit = $null
    foreach ($line in $Lines) {
        $fields = $line -split "`t"
        if ($fields.Count -lt 2) {
            continue
        }
        if ($fields[1] -eq "refs/tags/$($Name)^{}") {
            return $fields[0]
        }
        if ($fields[1] -eq "refs/tags/$Name") {
            $commit = $fields[0]
        }
    }
    return $commit
}

function Resolve-RemoteTarget {
    # Turns a -Tag value into the remote ref to fetch:
    #   ""        the remote's default branch, at its newest commit
    #   "latest"  the highest tag in version order
    #   anything  that exact tag; one that does not exist is an error
    # Returns @{ Ref; LocalRef; Commit; Label }, where Commit is what the remote reports right now.
    param(
        [string] $Url,
        [string] $Tag
    )

    if ($Tag -eq "") {
        $lines = @(git ls-remote --symref $Url HEAD)
        if ($LASTEXITCODE -ne 0) {
            throw "Could not reach $Url (git ls-remote failed)."
        }
        $branchRef = $null
        $commit = $null
        foreach ($line in $lines) {
            if ($line -match '^ref: (refs/heads/\S+)\tHEAD$') {
                $branchRef = $Matches[1]
            }
            elseif ($line -match '^([0-9a-f]{40,64})\tHEAD$') {
                $commit = $Matches[1]
            }
        }
        if (-not $branchRef -or -not $commit) {
            throw "Could not work out the default branch of $Url."
        }
        $branch = $branchRef.Substring("refs/heads/".Length)
        return @{
            Ref = $branchRef
            LocalRef = "refs/remotes/origin/$branch"
            Commit = $commit
            Label = "$branch (latest commit)"
        }
    }

    if ($Tag -eq "latest") {
        # versionsort.suffix=- sorts 0.6.8-rc1 before 0.6.8, so a release outranks its own release
        # candidates. A release candidate for a newer version still outranks an older release.
        $lines = @(git -c versionsort.suffix=- ls-remote --tags --sort=-v:refname $Url)
        if ($LASTEXITCODE -ne 0) {
            throw "Could not reach $Url (git ls-remote failed)."
        }
        $name = $null
        foreach ($line in $lines) {
            $ref = ($line -split "`t")[1]
            if ($ref -and -not $ref.EndsWith("^{}")) {
                $name = $ref.Substring("refs/tags/".Length)
                break
            }
        }
        if (-not $name) {
            throw "$Url has no tags, so there is no latest tag to use."
        }
        $label = "tag $name (latest)"
    }
    else {
        $name = $Tag
        $lines = @(git ls-remote --tags $Url "refs/tags/$Tag")
        if ($LASTEXITCODE -ne 0) {
            throw "Could not reach $Url (git ls-remote failed)."
        }
        $label = "tag $name"
    }

    $commit = Get-TagCommit -Lines $lines -Name $name
    if (-not $commit) {
        throw "Tag '$name' does not exist in $Url."
    }
    return @{
        Ref = "refs/tags/$name"
        LocalRef = "refs/tags/$name"
        Commit = $commit
        Label = $label
    }
}

function Remove-LinksInside {
    # Deletes every junction and directory symlink below $Path without following it. Remove-Item
    # on Windows PowerShell has a history of recursing into a junction's target, and the world link
    # inside Archipelago points at khimera_damg\ in this repository, so the links have to go
    # before anything deletes or cleans the tree around them. DirectoryInfo.Delete() on a reparse
    # point removes only the link.
    param(
        [string] $Path
    )

    foreach ($dir in ([System.IO.DirectoryInfo] $Path).GetDirectories()) {
        if ($dir.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            $dir.Delete()
        }
        else {
            Remove-LinksInside $dir.FullName
        }
    }
}

function Remove-Folder {
    param(
        [string] $Path
    )

    if (-not (Test-Path $Path)) {
        return
    }
    Remove-LinksInside $Path
    try {
        Remove-Item $Path -Recurse -Force -ErrorAction Stop
    }
    catch {
        throw ("Could not delete $Path ($($_.Exception.Message)). Something has it open, often a " +
               "terminal whose working directory is inside it.")
    }
}

function Remove-Clone {
    # Deletes the clone at $Path together with its git directory.
    param(
        [string] $Path
    )

    Remove-Folder $Path
    Remove-Folder (Get-CloneGitDir $Path)
}

function Get-PinnedCommit {
    # The commit the clone at $Path was set up at, or $null when its git directory is missing or
    # was not made by this tooling. The folder itself may be missing; a restore brings it back.
    param(
        [string] $Path
    )

    if (-not (Test-Path (Join-Path (Get-CloneGitDir $Path) "HEAD"))) {
        return $null
    }
    $gitArgs = Get-CloneGitArgs $Path
    $commit = git @gitArgs rev-parse --verify --quiet "$($PinnedRef)^{commit}"
    if ($LASTEXITCODE -ne 0 -or -not $commit) {
        return $null
    }
    return $commit.Trim()
}

function Install-Repository {
    # Makes $Path a depth-1 clone of $Url at $Ref, checked out detached, and pins that commit.
    # With $LocalRef the fetched ref is also kept under that name, so a tag stays a tag inside the
    # clone; without it, $Ref may be a bare commit id. Neither $Path nor its git directory may
    # exist. Returns the commit.
    param(
        [string] $Url,
        [string] $Path,
        [string] $Ref,
        [string] $LocalRef = ""
    )

    $gitDir = Get-CloneGitDir $Path
    foreach ($existing in @($Path, $gitDir)) {
        if (Test-Path $existing) {
            throw "$existing already exists."
        }
    }

    $refspec = $Ref
    if ($LocalRef) {
        $refspec = "+$($Ref):$LocalRef"
    }

    $gitArgs = Get-CloneGitArgs $Path
    try {
        # git init creates the git directory but not its parent, and the work tree has to exist
        # for the checkout.
        New-Item -ItemType Directory -Path (Split-Path $gitDir -Parent) -Force | Out-Null
        New-Item -ItemType Directory -Path $Path | Out-Null
        Invoke-Git -Arguments ($gitArgs + @("init", "--quiet", "--initial-branch=main")) `
            -Failure "git init failed for $Path."
        # init records the work tree as an absolute path. A relative one survives moving this
        # repository, and only matters to git run by hand: the scripts always pass --work-tree.
        Invoke-Git -Arguments ($gitArgs + @("config", "core.worktree", "../../$(Split-Path $Path -Leaf)")) `
            -Failure "Could not record the work tree of $Path."
        Invoke-Git -Arguments ($gitArgs + @("remote", "add", "origin", $Url)) `
            -Failure "Could not add the remote to $Path."
        Invoke-Git -Arguments ($gitArgs + @("fetch", "--depth", "1", "--no-tags", "origin", $refspec)) `
            -Failure "Fetching $Ref from $Url failed."

        $commit = git @gitArgs rev-parse --verify --quiet "FETCH_HEAD^{commit}"
        if ($LASTEXITCODE -ne 0 -or -not $commit) {
            throw "Could not read the fetched commit in $Path."
        }
        $commit = $commit.Trim()

        Invoke-Git -Arguments ($gitArgs + @("update-ref", $PinnedRef, $commit)) `
            -Failure "Could not record the pinned commit in $Path."
        Invoke-Git -Arguments ($gitArgs + @("-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach",
                                            $commit)) `
            -Failure "Checking out $commit in $Path failed."
    }
    catch {
        # A half-made clone is worth nothing, and would only fail the next run's checks.
        Remove-Clone $Path
        throw
    }
    return $commit
}

function Invoke-RepositorySetup {
    # The body of setup_<folder>.ps1. A folder that is already set up is left alone even when $Tag
    # now resolves to another commit: it may hold work in progress, so only -Force replaces it.
    param(
        [string] $Name,
        [string] $Url,
        [string] $Path,
        [string] $Tag,
        [switch] $Force
    )

    $gitDir = Get-CloneGitDir $Path
    if (((Test-Path $Path) -or (Test-Path $gitDir)) -and -not $Force) {
        $pinned = Get-PinnedCommit $Path
        if (-not $pinned) {
            if (-not (Test-Path $gitDir)) {
                throw ("$Path exists but has no git directory at $gitDir, so it is not a clone made by this " +
                       "setup. Rerun with -Force to replace it.")
            }
            throw "$gitDir exists but is not a clone made by this setup. Rerun with -Force to replace it."
        }
        if (-not (Test-Path $Path)) {
            throw ("$Path is missing, but its git directory at $gitDir is still there. Run the matching " +
                   "scripts\restore_*.ps1 to check it out again, or rerun with -Force to download it again.")
        }
        try {
            $target = Resolve-RemoteTarget -Url $Url -Tag $Tag
        }
        catch {
            Write-Warning "$Name is set up at $pinned; it could not be compared with $Url. $($_.Exception.Message)"
            return
        }
        if ($target.Commit -eq $pinned) {
            Write-Host "$Name already set up at $pinned, $($target.Label)."
        }
        else {
            Write-Warning ("$Name is set up at $pinned, but $($target.Label) is now $($target.Commit). " +
                           "Rerun with -Force to replace the folder with it.")
        }
        return
    }

    # Resolved before anything is deleted, so a mistyped tag leaves the existing folder in place.
    $target = Resolve-RemoteTarget -Url $Url -Tag $Tag
    if ((Test-Path $Path) -or (Test-Path $gitDir)) {
        Write-Host "Deleting the existing $Path and its git directory"
        Remove-Clone $Path
    }
    Write-Host "Cloning $Name, $($target.Label), from $Url"
    $commit = Install-Repository -Url $Url -Path $Path -Ref $target.Ref -LocalRef $target.LocalRef
    Write-Host "$Name set up at $commit in $Path"
}

function Invoke-RepositoryRestore {
    # The body of restore_<folder>.ps1. Puts $Path back to the commit it was set up at: every
    # tracked file as committed, and everything else deleted, ignored files included. A folder
    # deleted by hand is checked out again from its git directory. When that cannot be done in
    # place, or -Reclone asks for it, the folder and its git directory are deleted and that same
    # commit downloaded again. Returns $false when there is nothing to restore from (no usable git
    # directory, or the download failed); the caller then falls back to a fresh setup.
    param(
        [string] $Name,
        [string] $Path,
        [switch] $Reclone
    )

    $pinned = Get-PinnedCommit $Path
    if (-not $pinned) {
        return $false
    }
    $gitArgs = Get-CloneGitArgs $Path

    if (-not $Reclone) {
        try {
            if (Test-Path $Path) {
                Remove-LinksInside $Path
            }
            else {
                New-Item -ItemType Directory -Path $Path | Out-Null
            }
            Invoke-Git -Arguments ($gitArgs + @("-c", "advice.detachedHead=false", "checkout", "--force", "--quiet",
                                                "--detach", $pinned)) `
                -Failure "Checking out $pinned in $Path failed."
            # -ff also removes nested repositories, and -x ignored files: logs, host.yaml, __pycache__.
            Invoke-Git -Arguments ($gitArgs + @("clean", "-ffdxq")) -Failure "git clean failed in $Path."
            Write-Host "$Name restored in place to $pinned"
            return $true
        }
        catch {
            Write-Warning "Restoring $Name in place failed: $($_.Exception.Message) Downloading it again."
        }
    }

    $url = git @gitArgs config --get remote.origin.url
    if ($LASTEXITCODE -ne 0 -or -not $url) {
        return $false
    }

    Write-Host "Deleting $Path and its git directory, and downloading $pinned again"
    Remove-Clone $Path
    try {
        Install-Repository -Url $url.Trim() -Path $Path -Ref $pinned | Out-Null
    }
    catch {
        Write-Warning "Downloading $pinned again failed: $($_.Exception.Message)"
        return $false
    }
    Write-Host "$Name restored to $pinned"
    return $true
}
