<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->

# Running the ionium fuzzer locally

The fuzzer (<https://github.com/ionium-ap/Archipelago-fuzzer>) generates multiworlds against
a source checkout of Archipelago and reports failures. It runs entirely offline against your
working tree -- no release or published URL needed, so this should run before every tag. See
CLAUDE.md, "Distribution target: the ionium index", for why these specific checks matter.

## Prerequisite: a standalone Python interpreter

The fuzzer needs Archipelago running from source, which needs a real Python 3.11.9-3.13
install -- not the Windows Store version, and not the Python bundled inside the installed
Archipelago build at `C:\ProgramData\Archipelago` (that copy is a frozen PyInstaller app with
no `python.exe`, `pip`, or `venv` of its own, so it can't be pointed at an arbitrary script).

    scripts/setup_python.ps1

Downloads the official python.org installer and installs it, per-user and off PATH, into
`/python` at the repo root. `/python` is a plain gitignored folder (its own `.gitignore`, same
idiom as `.pytest_cache`/`.ruff_cache`), never touched outside this script. Pass `-Version` to
pick a different release, or `-Force` to reinstall.

## One-time setup

    scripts/run_fuzzer.ps1 -Setup

This creates a detached worktree of the `Archipelago` submodule fork under `_ignore_/ap-fuzz`
(so the submodule itself is never written to), clones the fuzzer into `/fuzzer` at the repo
root, copies `fuzz.py` and `hooks/` into the worktree root, and builds a venv at
`_ignore_/ap-fuzz/.venv` from that worktree's `requirements.txt`, using the interpreter at
`/python/python.exe` unless `-PythonExe` points somewhere else. `/fuzzer` is a plain,
gitignored folder like `/python` above -- the clone's own `.git` is stripped right after
cloning so a self-contained `.gitignore` can actually take effect (a nested `.git` would
otherwise make the outer repo treat the whole folder as an opaque untracked entry, invisible
to any `.gitignore` written inside it).

## Every run

    scripts/run_fuzzer.ps1

Rebuilds `khimera_damg.apworld` fresh from your current `worlds/khimera_damg` into
`_ignore_/ap-fuzz/custom_worlds/`, the same `Compress-Archive` step `scripts/build_apworld.ps1`
uses, then runs:

    fuzz.py -r 500 -j 16 -g khimera_damg -n 1

It has to be a real `.apworld` zip, not a directory link: Archipelago's own
`worlds/__init__.py` never extends `worlds.__path__` for a bare folder dropped in
`custom_worlds`, so a plain `import worlds` can never find a submodule living there -- this is
true upstream too, not a fork issue, confirmed by testing both side by side against this exact
worktree. Only `.apworld` zips get registered, through a meta-path finder built specifically
for that case. (The `Archipelago/custom_worlds/khimera_damg` directory link CLAUDE.md
describes elsewhere is unaffected by this -- it's for static analysis only, which reads files
directly and never goes through Python's import system.)

with the six hooks that count toward the index's 1% failure budget:
`gerpocalypse`, `indirect_conditions`, `item_location_count`,
`detect_rule_variable_capture_issues`, `check_placement_item_location_references`,
`detect_output_placement_changes`. Output lands in `_ignore_/ap-fuzz/fuzz_output`.

Pass `-FuzzArgs` to override the invocation, e.g. more generations, a wider YAML range, or a
fuzz-meta file once `fuzz-meta/khimera_damg.yaml` has constraints worth applying:

    scripts/run_fuzzer.ps1 -FuzzArgs @("-r", "500", "-j", "16", "-g", "khimera_damg", "-n", "1-3", "-m", "fuzz-meta/khimera_damg.yaml")

To also test against `empty-apworld` (<https://github.com/ionium-ap/empty-apworld>), the
100-free-location world the index uses to separate restrictive-start failures from real logic
bugs, place its `.apworld` under `_ignore_/ap-fuzz/custom_worlds/` alongside
`khimera_damg.apworld` and add `-g empty_apworld` (or whatever its registered name is) to
`-FuzzArgs`.

## Refreshing the fuzzer checkout

`-Setup` always re-clones `/fuzzer` fresh and re-copies `fuzz.py`/`hooks/` into the worktree,
so re-running it picks up the latest fuzzer release. It only skips the venv step if one
already exists at `_ignore_/ap-fuzz/.venv` -- delete that folder first to rebuild it (e.g.
after bumping the Python version with `scripts/setup_python.ps1 -Force`).
