<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->

# Running the ionium fuzzer locally

The fuzzer (<https://github.com/ionium-ap/Archipelago-fuzzer>) generates multiworlds against
a source checkout of Archipelago and reports failures. It runs entirely offline against your
working tree -- no release or published URL needed, so this should run before every tag.

In short:

    scripts/run_fuzzer.ps1 -Setup             # once, and again to refresh the fuzzer
    scripts/run_fuzzer.ps1                    # the failure rate the index measures
    scripts/run_fuzzer.ps1 -Pass checks       # each counted hook, one pass each
    scripts/run_fuzzer.ps1 -Pass canary       # proves the pipeline still reports failures

Read "Why passes" below before changing how the fuzzer is invoked.

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

This:

1. creates a detached worktree of the `Archipelago` submodule at `fuzz-env/ap-fuzz`, at the commit
   the submodule has checked out, so the submodule itself is never written to. If the worktree
   already exists but sits on another commit, it is moved to the submodule's (see "Keeping the
   worktree on the submodule's commit");
2. clones the fuzzer into `fuzz-env/fuzzer-clone`, and only once that succeeded replaces `/fuzzer`
   at the repo root with it. The clone's `.git` is stripped so the folder's own `.gitignore` takes
   effect (a nested `.git` would make the outer repo treat it as an opaque untracked entry), and
   the commit it was cloned at is kept in `fuzzer/COMMIT`;
3. copies `fuzz.py` and `hooks/` into the worktree root, replacing the old `hooks/` folder rather
   than copying over it, so a hook removed upstream does not linger;
4. builds a venv at `fuzz-env/ap-fuzz/.venv` from the worktree's `requirements.txt`, using
   `/python/python.exe` unless `-PythonExe` points somewhere else, if there is no venv yet. An
   existing venv is kept, and only gets the requirements reinstalled when step 1 moved the
   worktree;
5. runs `scripts/fuzzer/build_empty_apworld.ps1 -Force`, described under "The Empty world".

Every step stops the setup on failure and says why. If `/fuzzer` cannot be deleted -- usually
because a terminal is standing inside it -- the new clone is left in `fuzz-env/fuzzer-clone` and
the old copy stays where it was.

Re-run `-Setup` to pick up a newer fuzzer or empty-apworld. Delete `fuzz-env/ap-fuzz/.venv` first
to rebuild the venv from scratch (e.g. after `scripts/setup/setup_python.ps1 -Force`, which also
wants `scripts/setup/setup_build_env.ps1 -Force` so `py-env` is rebuilt on the same interpreter).

Everything the fuzzer needs lives under `fuzz-env/`, which is gitignored: the worktree
`fuzz-env/ap-fuzz` (with its venv, `custom_worlds/`, `static_worlds/` and `fuzz_runs/`), the
`empty-apworld` clone `fuzz-env/empty-apworld`, and short-lived build folders the scripts create
and remove there. The fuzzer clone itself stays at `/fuzzer`.

## Keeping the worktree on the submodule's commit

The apworld is built against the `Archipelago` submodule and fuzzed in the worktree, so the two
have to be on the same core. Before every run, and as the first step of `-Setup`,
`Sync-FuzzWorktree` in `run_fuzzer.ps1` compares the worktree's commit with the one the submodule
has checked out:

- no worktree yet: it is created at the submodule's commit;
- same commit: nothing happens;
- different commit: the worktree is checked out at the submodule's commit. Both share the
  submodule's object store, so the commit is always there and nothing is fetched. A plain run then
  reinstalls the worktree's requirements into the venv (a newer core can need other packages) and
  rebuilds `empty.apworld` from the existing clone (a newer core can change the container version
  its manifest has to carry); `-Setup` does both as part of its own steps.

Only changes to tracked files can be lost or block a checkout. Everything the fuzzer adds to the
worktree is untracked and survives the move. If the worktree does have tracked changes, the sync
refuses, lists them, and the run stops before any pass.

Moving the worktree changes git state in the worktree, never in `Archipelago/`:
`git -C Archipelago status` stays clean, and `git -C Archipelago worktree list` shows the
worktree's new commit.

## Every run

    scripts/run_fuzzer.ps1 [-Pass <pass>[,<pass>...]] [-Runs 500] [-Jobs 16] [-Yamls 1] [-Timeout 15]

Each run:

1. moves the worktree to the submodule's commit if it is anywhere else (see above);
2. builds `khimera_damg.apworld` fresh through `scripts/build_apworld.ps1`, checks that the build
   succeeded and produced a new file, and copies it into `fuzz-env/ap-fuzz/custom_worlds/`
   (`-SkipBuild` reuses the copy already there, with a warning);
3. runs each requested pass through `scripts/fuzzer/run_fuzz_pass.ps1`;
4. prints a summary table and exits non-zero unless every pass came back `ok`.

It goes through the build script rather than zipping the folder directly because a hand-made
zip carries the source `archipelago.json`, which deliberately omits `version` and
`compatible_version`; without those, Archipelago cannot read the manifest and loads the world
with no version metadata at all.

It also has to be a real `.apworld` zip, not a directory link: Archipelago's own
`worlds/__init__.py` never extends `worlds.__path__` for a bare folder dropped in
`custom_worlds`, so a plain `import worlds` can never find a submodule living there -- this is
true upstream too, not a fork issue. Only `.apworld` zips get registered, through a meta-path
finder built specifically for that case. (The junction at `Archipelago/worlds/khimera_damg` is
a different mechanism and is unaffected: it makes the world load as a plain folder from the
submodule's own `worlds/` directory, which is both what static analysis reads and what the
apworld build component expects.)

### Passes

| Pass | Hooks loaded | Empty | `--skip-output` | Fails when |
|---|---|---|---|---|
| `rate` (default) | none | yes | no | the failure rate is 1% or more |
| `gerpocalypse` | `gerpocalypse` | no (the hook adds Kingdom Hearts) | yes | any failure |
| `indirect_conditions` | that hook | yes | yes | any failure |
| `item_location_count` | that hook | yes | yes | any failure |
| `detect_rule_variable_capture_issues` | that hook | yes | yes | any failure |
| `check_placement_item_location_references` | that hook | yes | yes | any failure |
| `detect_output_placement_changes` | that hook | yes | **no** | any failure |
| `determinism` | `determinism` | yes | yes | any failure; runs at half the jobs and twice the timeout |

`checks` expands to the six counted passes and `all` to `rate` followed by them. `determinism` and
`canary` are never part of either; ask for them by name.

The `rate` pass is the index's measurement: failures plus timeouts, divided by generations that
did not end in an `OptionError`. It adds `--dump-ignored`, because this world rolls no invalid
option combinations, so an ignored generation is worth a look; the summary flags any.

A check pass has no rate. Its hook reclassifies everything it is not testing, so its counts say
only whether that one hook found anything.

`-Yamls` takes a number or a range such as `1-3`: that many Khimera slots per generation, with
the Empty slot on top.

`-ExtraArgs` adds arguments to every pass. It refuses `--hook` (pick a pass instead),
`--with-static-worlds` together with `gerpocalypse` (the hook would drop it), and
`--skip-output` for a pass that must run output.

### The fuzz-meta file

`fuzz-meta/khimera_damg.yaml` is passed with `-m` by default, as an absolute path, because
`fuzz.py` runs from the worktree where a relative path does not exist. `-NoMeta` leaves it out,
and `-Meta <path>` points at another file.

It currently holds an empty mapping under the game name and no constraints. The key must stay
even while empty: a file with no mapping at all loads as `None`, and the fuzzer crashes with
`'NoneType' object has no attribute 'get'` before any generation. The game name contains a
colon, so the key is quoted.

### Results

Every run gets a folder, `fuzz-env/ap-fuzz/fuzz_runs/<timestamp>/`, holding:

- `run.json` -- the parameters, the SHA-256 of the fuzzed apworld, and the commits of this
  repository, the fuzzer worktree and the fuzzer itself;
- one folder per pass, with `command.txt` (the exact `fuzz.py` command line), fuzz.py's
  `report.json`, its `error/` folder of failing YAMLs and logs, and `result.json` (counts, rate,
  verdict, notes, and the five most frequent error messages).

`fuzz.py` itself writes to `fuzz-env/ap-fuzz/fuzz_output` and wipes that folder at the start of
every run; the pass script moves its content into the archive as soon as the pass ends. Old run
folders are never deleted automatically.

A verdict is one of `ok`, `fail`, `error` (the pass could not start, or `fuzz.py` crashed) or
`stalled` (`fuzz.py` gave up on generations whose workers died; the counts cover only what
finished).

### The canary

    scripts/run_fuzzer.ps1 -Pass canary

`scripts/fuzzer/build_canary_apworld.ps1` writes a ten-location world, `kdamg_canary`, whose pool
is one item short and whose victory needs an item that does not exist, into the worktree's
`custom_worlds/`. The canary then runs the `rate` and `item_location_count` passes over it,
capped at 50 generations, and expects every one of them to fail. It removes the world again
afterwards, so it is never loaded during a real measurement.

Run it after changing anything in this pipeline, or after a fuzzer update. A canary pass that
comes back `fail` means failures are being hidden.

## The Empty world

`empty-apworld` (<https://github.com/ionium-ap/empty-apworld>) is the 100-free-location world the
index measures the failure rate with. Having it in every generation separates a restrictive start
from a real logic failure.

`scripts/fuzzer/build_empty_apworld.ps1` clones it into `fuzz-env/empty-apworld`, repacks it into
`fuzz-env/ap-fuzz/custom_worlds/empty.apworld`, and checks the result loads. The repack exists
for the manifest reason above: upstream's `archipelago.json` omits `version` and
`compatible_version` just like ours does, so the script injects both, taking
`container_version` out of the worktree's own `worlds/Files.py`. Run it directly with `-Force`
to re-clone and rebuild.

The passes add the Empty slot through the fuzzer's own `with_empty` hook
(`hooks/with_empty.py`), the same route the index uses. It leaves outcomes untouched, so it can
sit next to a checking hook. It writes an Empty YAML to a temporary folder and points
`--with-static-worlds` there; outside the index's container it does not load `empty.apworld`
itself, and relies on the world already being registered, which `custom_worlds/empty.apworld`
provides. It is always loaded first, so if Empty is missing its worker setup fails before any
other hook is registered, and the error reaches the report as a plain failure.

The script also writes `fuzz-env/ap-fuzz/static_worlds/empty.yaml`, for running `fuzz.py` by hand
with `--with-static-worlds static_worlds` instead of the hook.

## Why passes

Each fuzzer hook is written to be run on its own. A hook's `reclassify_outcome` turns every
outcome it is not testing into a success (or an `OptionError`), and `fuzz.py` applies every
loaded hook's reclassification in turn. The previous version of `run_fuzzer.ps1` loaded all six
counted hooks in one run, and with that combination:

- `gerpocalypse` turns anything without "no connected region" in its message into a success.
  Fill errors, pool/location mismatches, indirect-condition and capture errors, and timeouts all
  disappear there, and `item_location_count` does the same for anything that is not its own
  mismatch.
- `gerpocalypse` also replaces `--with-static-worlds` with a Kingdom Hearts YAML of its own, so
  the Empty slot is never added while it is loaded.
- `detect_output_placement_changes` wraps only `generate_output`, so under `--skip-output` it
  never fires, and `fill_slot_data` is never exercised either.

That run reported 0 failures whatever the world did. The pass table above is the fix: one
checking hook per pass, Empty wherever it can be, and output run where a hook needs it. The
canary is there to notice if the pipeline ever drifts back.

`gerpocalypse` needs the Kingdom Hearts world (`worlds/kh1`, present in the worktree). Without
it, the hook's worker setup raises inside every generation and its own reclassification would
turn that into a success, so the pass script refuses to start the pass when the world is missing.

## Running fuzz.py by hand

For anything the passes do not cover, run `fuzz.py` from `fuzz-env/ap-fuzz` with the worktree's
venv, after a normal run has installed the current apworld. Keep to one checking hook per run:

    .venv\Scripts\python.exe fuzz.py -r 500 -j 16 -g khimera_damg -n 1-5 --hook hooks.with_empty:Hook
