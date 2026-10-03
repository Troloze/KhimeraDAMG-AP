<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->

# Running the ionium fuzzer locally

The fuzzer (<https://github.com/ionium-ap/Archipelago-fuzzer>) generates multiworlds against
a source checkout of Archipelago and reports failures. It runs entirely offline against your
working tree -- no release or published URL needed, so this should run before every tag. The
six hooks it runs by default are the ones that count toward the ionium index's 1% generation
failure budget.

## Prerequisite: a configured clone

The fuzzer needs Archipelago running from source, which needs a real Python 3.11.9-3.13
install -- not the Windows Store version, and not the Python bundled inside the installed
Archipelago build at `C:\ProgramData\Archipelago` (that copy is a frozen PyInstaller app with
no `python.exe`, `pip`, or `venv` of its own, so it can't be pointed at an arbitrary script).

    scripts/setup.ps1

This runs all three setup steps in order. The fuzzer needs every one of them:
`scripts/setup/setup_python.ps1` downloads the official python.org installer and installs it,
per-user and off PATH, into `/python` at the repo root; `setup_world_link.ps1` links the apworld
into the submodule's `worlds/` folder; and `setup_build_env.ps1` builds the `py-env` venv the
apworld build step needs. `/python` is a plain gitignored folder (its own `.gitignore`, same
idiom as `.pytest_cache`/`.ruff_cache`), never touched outside that script. Pass `-Version` to
`setup_python.ps1` to pick a different release, or `-Force` to any of them to redo the step.

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

It finishes by running `scripts/build/build_empty_apworld.ps1`, which sets up the
`empty-apworld` side described at the end of the next section.

## Every run

    scripts/run_fuzzer.ps1

Calls `scripts/build_apworld.ps1` to build `khimera_damg.apworld` fresh from your current
`worlds/khimera_damg`, copies it into `_ignore_/ap-fuzz/custom_worlds/`, then runs:

    fuzz.py -r 500 -j 16 -g khimera_damg -n 1

It goes through the build script rather than zipping the folder directly because a hand-made
zip carries the source `archipelago.json`, which deliberately omits `version` and
`compatible_version`; without those, Archipelago cannot read the manifest and loads the world
with no version metadata at all.

It also has to be a real `.apworld` zip, not a directory link: Archipelago's own
`worlds/__init__.py` never extends `worlds.__path__` for a bare folder dropped in
`custom_worlds`, so a plain `import worlds` can never find a submodule living there -- this is
true upstream too, not a fork issue, confirmed by testing both side by side against this exact
worktree. Only `.apworld` zips get registered, through a meta-path finder built specifically
for that case. (The junction at `Archipelago/worlds/khimera_damg` is a different mechanism and
is unaffected: it makes the world load as a plain folder from the submodule's own `worlds/`
directory, which is both what static analysis reads and what the apworld build component
expects.)

The run uses the six hooks that count toward the index's 1% failure budget:
`gerpocalypse`, `indirect_conditions`, `item_location_count`,
`detect_rule_variable_capture_issues`, `check_placement_item_location_references`,
`detect_output_placement_changes`. Output lands in `_ignore_/ap-fuzz/fuzz_output`.

Pass `-FuzzArgs` to override the invocation, e.g. more generations, a wider YAML range, or a
fuzz-meta file once `fuzz-meta/khimera_damg.yaml` has constraints worth applying:

    scripts/run_fuzzer.ps1 -FuzzArgs @("-r", "500", "-j", "16", "-g", "khimera_damg", "-n", "1-3", "-m", "fuzz-meta/khimera_damg.yaml")

`-Setup` also places `empty-apworld` (<https://github.com/ionium-ap/empty-apworld>), the
100-free-location world the index measures the failure rate with, so there is nothing to do by
hand. `scripts/build/build_empty_apworld.ps1` clones it into `_ignore_/empty-apworld`, repacks
it into `_ignore_/ap-fuzz/custom_worlds/empty.apworld`, and writes a one-slot player yaml to
`_ignore_/ap-fuzz/static_worlds/empty.yaml`. The repack exists for the manifest reason above:
upstream's `archipelago.json` omits `version` and `compatible_version` just like ours does, so
the script injects both, taking `container_version` out of the worktree's own `worlds/Files.py`
rather than hardcoding it. Run it directly with `-Force` to re-clone and rebuild.

`--with-static-worlds` copies every yaml in that folder into each generation, so the Empty slot
is present in all of them rather than a random subset -- that is what separates a restrictive
start from a real logic failure. Its path is relative to the fuzzer worktree, where `fuzz.py`
runs. The full command, under the conditions the index measures:

    scripts/run_fuzzer.ps1 -FuzzArgs @("-r", "500", "-j", "16", "-g", "khimera_damg", "-n", "1-5", "--with-static-worlds", "static_worlds", "--skip-output")

## Refreshing the fuzzer checkout

`-Setup` always re-clones `/fuzzer` fresh and re-copies `fuzz.py`/`hooks/` into the worktree,
and re-clones `empty-apworld` the same way, so re-running it picks up the latest of both. It
only skips the venv step if one already exists at `_ignore_/ap-fuzz/.venv` -- delete that folder
first to rebuild it (e.g. after bumping the Python version with
`scripts/setup/setup_python.ps1 -Force`, which also wants `scripts/setup/setup_build_env.ps1
-Force` so `py-env` is rebuilt on the same interpreter).
