<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->

# Running the ionium fuzzer locally

The fuzzer (<https://github.com/ionium-ap/Archipelago-fuzzer>) generates multiworlds against
a source checkout of Archipelago and reports failures. It runs entirely offline against your
working tree -- no release or published URL needed, so this should run before every tag.

Read "What a run can and cannot tell you" below before trusting a result. The default run passes
all six counted hooks at once, and that combination cannot report a failure.

## Prerequisite: a configured clone

The fuzzer needs Archipelago running from source, which needs a real Python 3.11.9-3.13
install -- not the Windows Store version, and not the Python bundled inside the installed
Archipelago build at `C:\ProgramData\Archipelago` (that copy is a frozen cx_Freeze app with
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

It finishes by running `scripts/fuzzer/build_empty_apworld.ps1`, which sets up the
`empty-apworld` side described at the end of the next section.

## Every run

    scripts/run_fuzzer.ps1

Calls `scripts/build_apworld.ps1` to build `khimera_damg.apworld` fresh from your current
`worlds/khimera_damg`, copies it into `_ignore_/ap-fuzz/custom_worlds/`, then runs:

    fuzz.py -r 500 -j 16 -g khimera_damg -n 1 --skip-output

followed by a `--hook` argument for each of the six counted hooks.

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

The run always appends the six hooks that count toward the index's 1% failure budget:
`gerpocalypse`, `indirect_conditions`, `item_location_count`,
`detect_rule_variable_capture_issues`, `check_placement_item_location_references`,
`detect_output_placement_changes`. There is no switch to leave them out. Output lands in
`_ignore_/ap-fuzz/fuzz_output`.

Pass `-FuzzArgs` to override the rest of the invocation, e.g. more generations or a wider YAML
range. The hooks are still appended:

    scripts/run_fuzzer.ps1 -FuzzArgs @("-r", "500", "-j", "16", "-g", "khimera_damg", "-n", "1-3", "--skip-output")

A fuzz-meta file goes in the same way, with `-m`, but two things stop
`fuzz-meta/khimera_damg.yaml` from working today. It is comments only, so `yaml.safe_load` returns
`None` and the fuzzer crashes with `'NoneType' object has no attribute 'get'` before any
generation; it needs at least an empty mapping keyed by the game name first. And `fuzz.py` runs
from `_ignore_/ap-fuzz`, where a relative `fuzz-meta/...` path does not exist, so pass the
absolute path to the file.

`-Setup` also places `empty-apworld` (<https://github.com/ionium-ap/empty-apworld>), the
100-free-location world the index measures the failure rate with, so there is nothing to do by
hand. `scripts/fuzzer/build_empty_apworld.ps1` clones it into `_ignore_/empty-apworld`, repacks
it into `_ignore_/ap-fuzz/custom_worlds/empty.apworld`, and writes a one-slot player yaml to
`_ignore_/ap-fuzz/static_worlds/empty.yaml`. The repack exists for the manifest reason above:
upstream's `archipelago.json` omits `version` and `compatible_version` just like ours does, so
the script injects both, taking `container_version` out of the worktree's own `worlds/Files.py`
rather than hardcoding it. Run it directly with `-Force` to re-clone and rebuild.

`--with-static-worlds` copies every yaml in that folder into each generation, so the Empty slot
is present in all of them rather than a random subset -- that is what separates a restrictive
start from a real logic failure. Its path is relative to the fuzzer worktree, where `fuzz.py`
runs.

That only holds while `gerpocalypse` is not loaded, because it overwrites `--with-static-worlds`
(see below). Through `run_fuzzer.ps1`, which always loads it, passing
`--with-static-worlds static_worlds` has no effect. The fuzzer's own `with_empty` hook
(`hooks/with_empty.py`) is the other way in, and the one the index uses: it writes an Empty YAML
to a temporary folder and points `--with-static-worlds` there. Outside the index's container it
does not load `empty.apworld` itself; it relies on the world already being registered, which the
`custom_worlds/empty.apworld` built above provides. Either route works in a pass that does not
load `gerpocalypse`.

## What a run can and cannot tell you

Each fuzzer hook is written to be run on its own, in a separate pass. A hook's
`reclassify_outcome` turns every outcome it is not testing into a success (or an `OptionError`),
and `fuzz.py` applies every loaded hook's reclassification in turn. With all six loaded together:

- `gerpocalypse` runs first and turns anything without "no connected region" in its message into
  a success. Fill errors, pool/location mismatches, indirect-condition and capture errors, and
  timeouts all disappear there. Even its own GER failures are turned into an `OptionError` by the
  next hook and back into a success by the one after.
- `gerpocalypse` also replaces `--with-static-worlds` with a Kingdom Hearts YAML of its own, so
  the Empty slot is never added while it is loaded.
- `detect_output_placement_changes` wraps only `generate_output`. Under `--skip-output`, which the
  default run passes, it never fires, and `fill_slot_data` is never exercised either.

So the default run reports 0 failures regardless of the world's logic, and a clean result from it
is not evidence for the 1% budget. Meaningful results need separate passes:

- **The failure rate:** one pass with no checking hooks and the Empty world in every generation.
- **Each counted hook:** one pass per hook, with only that hook loaded. Leave out
  `--skip-output` for `detect_output_placement_changes`.

`run_fuzzer.ps1` cannot run any of these, since it always appends all six hooks. Until it can,
run `fuzz.py` directly with the worktree's venv. First let the script build and copy the current
apworld into `custom_worlds/`; a single generation is enough for that:

    scripts/run_fuzzer.ps1 -FuzzArgs @("-r", "1", "-g", "khimera_damg", "-n", "1", "--skip-output")

Then, from `_ignore_/ap-fuzz`:

    .venv\Scripts\python.exe fuzz.py -r 500 -j 16 -g khimera_damg -n 1-5 --hook hooks.with_empty:Hook
    .venv\Scripts\python.exe fuzz.py -r 500 -j 16 -g khimera_damg -n 1 --skip-output --hook hooks.item_location_count:Hook

## Refreshing the fuzzer checkout

`-Setup` always re-clones `/fuzzer` fresh and re-copies `fuzz.py`/`hooks/` into the worktree,
and re-clones `empty-apworld` the same way, so re-running it picks up the latest of both. It
only skips the venv step if one already exists at `_ignore_/ap-fuzz/.venv` -- delete that folder
first to rebuild it (e.g. after bumping the Python version with
`scripts/setup/setup_python.ps1 -Force`, which also wants `scripts/setup/setup_build_env.ps1
-Force` so `py-env` is rebuilt on the same interpreter).
