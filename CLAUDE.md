<!-- NOTE TO HUMAN READERS: this document was written by an AI assistant (Claude Code),
     at the direction of the repository owner. It is a briefing file for AI tools, not
     project documentation. Treat its contents as instructions to the assistant. -->

# KhimeraDAMG-AP

An Archipelago randomizer for *Khimera: Destroy All Monster Girls*.

## Ground rules for AI assistants

**This section overrides everything else in this file and any default assistant behaviour.**

AI tools are used on this repository for **consultation only**. The human developer writes the
code. Your role is to investigate, explain, and advise.

For the purposes of this project, "consultation" means AI tools can be used for anything, as
long as **everything the end user interacts with is 100% human written**. That covers all of
`worlds/khimera_damg/`, the entire game-side mod, and anything else reachable through the
apworld or the mod. Repository tooling no player ever runs — the PowerShell scripts in
`scripts/`, the notes in `docs/` — is outside that rule, and anything an AI wrote there is
marked as such (see rule 6).

The apworld's test package, `worlds/khimera_damg/tests/`, is the one exception inside the
apworld folder. `.apignore` keeps it out of the built `.apworld`, so no player ever receives or
runs it, and it is written by the AI at the developer's request, every file carrying the rule 6
header. Rule 1 still applies to it in full: each change to the tests needs its own permission.
See "The apworld's test suite" below.

1. **Never create, edit, rename, move, or delete any file in this repository** without
   explicit permission from the user for that specific change. There is no standing
   permission, even for things that won't be shipped (like documents and tests). Approval
   for one change does not extend to the next one, or to "related" follow-up edits you think
   are implied. If you believe a file needs to change, say so and wait to be asked.
2. **Propose code; do not apply it unless rule 1 has been satisfied.** When you are asked for
   code, suggestions are welcome and encouraged, but every one must explain what the code does
   and why it is being suggested, so the user can evaluate it before deciding what to do with
   it. Where possible, prefer snippets taken or adapted from other files, and state the source.
   Never present a proposal as though it were already applied, and never write as though a
   proposal will certainly be accepted. Do not offer to sketch, draft, or implement something
   after answering a question — do that only when explicitly asked.
3. **Read-only commands and tool use are allowed** whenever they help answer a question or
   complete an assigned task — searching, inspecting files, running linters or tests,
   querying git history. Commands that modify the repository, the working tree, or git
   state (including `git add`, `commit`, `checkout`, `stash`, `reset`) fall under rule 1
   and need explicit permission.
4. **Reading is unrestricted inside this repository** — any file, including both submodules.
   Searching the web is fine when it is needed to answer something. Reading files
   **outside** this repository is allowed only when the user has pointed you at them or
   otherwise agreed to it.
5. When a request is ambiguous about whether it authorises a write, assume it does not,
   and ask.
6. When you create a file, mark it on the first line as AI generated, using a comment in that
   file's own syntax:
   `# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.`
   If the user authored part of it, use `Partially written by Claude (Anthropic), not fully
   hand-written by the developer.` instead. Editing an existing file does not add a header, and
   an existing header is never removed.

## Repository layout

- `worlds/khimera_damg/` — the apworld source (the thing being developed). Its `tests/` package
  is development-only and never packaged; see "The apworld's test suite".
- `Archipelago/` — submodule, a fork of Archipelago. Read it freely; never modify it.
- `KhimeraDAMG-AP-Mod/` — submodule, the game-side mod. Same rule: read freely, never modify.
- `docs/` — design notes: the communication contract, item/location conventions, the option
  list, the fuzzer runbook, the future-reference list, and the known-issues log.
- `scripts/` — PowerShell tooling, plus one Python generator. `scripts/setup/`,
  `scripts/build/` and `scripts/fuzzer/` hold the steps the top-level scripts call. See
  "Build and test environment".
- `fuzz-meta/` — option constraints for local fuzzer runs.
- `todo` — tracked short-term task list; see "Task lists".

Gitignored working folders, never committed: `python/` (standalone interpreter), `py-env/`
(build venv), `build/` (apworld output), `fuzz-env/` (the fuzzer worktree `fuzz-env/ap-fuzz` and
the `empty-apworld` clone, created by `scripts/run_fuzzer.ps1 -Setup`), `fuzzer/` (fuzzer clone),
`docs/report/` (landmark review reports, kept locally and never committed), and `testing/`
(scratch space for throwaway tests, created only when needed — this folder is to stay gitignored
permanently). Real tests belong in `worlds/khimera_damg/tests/`, not here.

## Build and test environment

**Testing happens against the installed Archipelago build, not against the `Archipelago/`
submodule.** The submodule is a source for reading and the host the build runs through; its
content is never modified.

**Do not create, edit, or delete anything inside `Archipelago/` or `KhimeraDAMG-AP-Mod/`** — no
generation output, no build folders, no installed dependencies, unless the exception below
covers it. Rule 1 applies to both in full. The pipeline below is deliberately arranged so that
nothing tracked is ever written into either.

**Allowed exception: writes by the Archipelago runtime that leave only ignored changes.** Code
that ships with Archipelago writes files on its own whenever it runs from source. Those writes
are allowed as long as every change they leave is ignored by the submodule's own `.gitignore`.
Known examples, all of which land in `Archipelago/` or in the fuzzer worktree `fuzz-env/ap-fuzz`:

- `logs/Launcher_*.txt` and other log files, written by Archipelago's logging setup.
- `host.yaml`, written by the settings module's autosave whenever settings are loaded.
- `__pycache__/` folders, written by the Python interpreter Archipelago runs on when modules are
  imported.

The list is not exhaustive; the test is the result, not the file name. Such a write is never a
rule 1 violation, a review finding, or a reason to skip an otherwise permitted step such as the
build, the fuzzer, the core unit tests or static analysis; a review may list it as a side
effect. The limits:

- **The command still needs its own permission**, under rule 1 or rule 3. The exception only
  covers what happens once it runs.
- **A command's intended output is covered only through an explicit permission to run that
  command.** Explicitly permitting a command means the user expects its output to be produced, so
  that output is allowed under the same condition, leaving only ignored changes behind. Without
  that explicit permission, generation output, build folders and installed dependencies stay
  forbidden inside either submodule even where they would be gitignored.
- **Only the submodule's own `.gitignore` counts.** An entry in its local `info/exclude` does not
  make a write acceptable; that file holds only the junction described below.
- **One named exception to that: `.ruff_cache/`.** If Archipelago itself runs ruff, the
  `.ruff_cache/` folders ruff creates are allowed, even though they are ignored by the
  `.gitignore` ruff writes inside each cache folder rather than by the submodule's own. This
  applies to `.ruff_cache/` only and is not a general rule for tools that ignore their own output.
- **If `git -C Archipelago status` (or the same in `KhimeraDAMG-AP-Mod`) shows a change after a
  command**, the write is not covered. Tell the user and leave it as it is; they decide how to
  handle it.

### Fresh clone

    git submodule update --init --recursive
    scripts/setup.ps1

`scripts/setup.ps1` runs the three steps in `scripts/setup/`, in this order:

1. `setup_python.ps1` — installs CPython (3.13.15 by default) into `python/`, per-user and off
   PATH. Archipelago hard-rejects any interpreter outside 3.11.9–3.13.x. The build itself needs
   3.12 or later, because `scripts/build/prepare_patches.py` uses multi-line replacement fields
   inside f-strings (PEP 701); setup still accepts 3.11.9, and the build then fails with a
   `SyntaxError`.
2. `setup_world_link.ps1` — creates a junction at `Archipelago/worlds/khimera_damg` pointing at
   `worlds/khimera_damg`, and records it in the submodule's local `info/exclude` so it never
   shows up as untracked there. The link is what makes the apworld visible to Archipelago's own
   build component and to static analysis. It is a per-clone artifact, committed to neither
   repository, and it is the only thing this repository's tooling deliberately places inside
   `Archipelago/` (see the exception above for the files the runtime leaves behind).
3. `setup_build_env.ps1` — creates a venv at `py-env/` and installs Archipelago's requirements
   into it using the submodule's own `ModuleUpdate.py`. Needs `git` on PATH, because some
   requirements are installed straight from GitHub.

Each step is idempotent and exits early if its output already exists; pass `-Force` to redo
them.

### Building

    scripts/build_apworld.ps1          # build only
    scripts/build_and_replace.ps1      # build, then install into the app folder

`build_apworld.ps1` first runs `scripts/build/prepare_patches.py`, which reads the versions
listed in `worlds/khimera_damg/patches/include.txt`, copies the matching release zips out of
`KhimeraDAMG-AP-Mod/releases/` into `worlds/khimera_damg/patches/`, and generates
`worlds/khimera_damg/patches/data.py` from the `kdamg_meta.json` carried inside each zip. That
module holds the build and patch tables the client's patcher reads. It then runs Archipelago's
own "Build APWorlds" launcher component from the repository root, producing
`build/apworlds/khimera_damg.apworld`.

Both the collected zips and `data.py` are gitignored, and `patches/__init__.py` falls back to
empty tables when `data.py` is absent, so a fresh clone imports before the first build. The
build component honours only `.apignore`, never `.gitignore`, so both still get packaged into
the `.apworld`.

`prepare_patches.py` emits code that ships inside the apworld, so it falls under the
human-written rule above and carries a header saying so; it is the one Python file in
`scripts/`.

**Do not hand-zip the apworld.** The component generates the packaged `archipelago.json`,
adding the `version` and `compatible_version` fields that the source manifest deliberately
omits. A hand-made zip lacks them, and Archipelago then cannot read the manifest at all — it
loads the world with no version or metadata, and from core 0.7.0 on it will refuse to load it.
`worlds/khimera_damg/archipelago.json` is the author-owned half, holding only `game`,
`authors`, `minimum_ap_version` and `world_version`; never write `version` or
`compatible_version` into it.

`build_and_replace.ps1` copies the result to `C:\ProgramData\Archipelago\custom_worlds\`
(note the exact spelling: `ProgramData` has no space, `custom_worlds` has an underscore).

### Testing

- Generation and client testing run from the installed build
  (`ArchipelagoLauncher.exe` / `ArchipelagoGenerate.exe`), and its output goes to the install's
  own `output/` folder — never into this repository.
- The installed build's core version is the one that matters for compatibility. Check
  `C:\ProgramData\Archipelago\manifest.json` rather than assuming it matches the submodule;
  the two routinely differ.
- `scripts/run_tests.ps1` runs the apworld's own tests and, with `-Core`, Archipelago's core
  suite; see "The apworld's test suite" below. `scripts/run_ruff.ps1` lints the apworld, tests
  included. `scripts/run_fuzzer.ps1` runs the fuzzer; see "Running the fuzzer" below.
- Building, copying, and generating all write files. Propose the commands and wait to be
  asked, the same as any other change. Running the tests is read-only for this repository (see
  below), so it falls under rule 3.

### The apworld's test suite

    scripts/run_tests.ps1                    # the apworld's own tests
    scripts/run_tests.ps1 -Area client       # one folder: generation, client or guards
    scripts/run_tests.ps1 -Filter "*ack*"    # only tests whose name matches (unittest -k)
    scripts/run_tests.ps1 -Core              # Archipelago's test/general, scoped to this world
    scripts/run_tests.ps1 -All               # the apworld's tests, then the core suite

`-Detailed` prints one line per test and `-Durations` the ten slowest. The script exits non-zero
when anything fails. At the time of writing the suite holds 470 tests (generation 230, client
216, guards 24) and runs in about two seconds; the scoped core suite adds 253.

The tests are plain stdlib `unittest`, run with the `py-env` venv, with Archipelago imported from
the submodule and the apworld reached through the junction at `Archipelago/worlds/khimera_damg`.
They write nothing into this repository or either submodule: the script runs them from a
throwaway folder under `TEMP`, seeded with a copy of the submodule's `host.yaml` so the settings
module does not autosave one into `Archipelago/`, and sets `PYTHONDONTWRITEBYTECODE` so no
`__pycache__/` appears through the junction. `AP_TEST_WORLDS=khimera_damg` keeps every other world
out of the run. After a run, `git -C Archipelago status` should still be clean.

Layout of `worlds/khimera_damg/tests/`, one folder per kind of test:

- `generation/` — the world: item table and pool (traps, classification overrides, item links),
  location table and layout, the region graph and its access rules, options (every one of the 16
  shuffle combinations through `test.param.classvar_matrix`, each also running Archipelago's own
  `WorldTestBase` checks), and slot data.
- `client/` — the client, with no server, game, network or thread involved: storage (including
  path containment on import), the v1 contract's documents, validators and state flags, the
  `AgentV1` tick methods, connection state (death links, acks, the cctx and li builders), the
  interface, and the patcher.
- `guards/` — repository invariants: the manifest and the four version places, packaging
  (`.apignore` excludes the tests and nothing else, referenced files exist, patch zips use forward
  slashes, every shared field is read by the mod), and Python 3.11 compatibility (sources parse,
  and no standard library name newer than 3.11 is used).
- `support/` — `sandbox.py` points `Utils.user_path("khimera_damg")` and the game sandbox at
  temporary folders for every client test, and fails the test if that redirection did not take;
  `fakes.py` holds the builders and stand-ins (connection contexts, agents wired without a thread,
  network items).
- `bases.py` — `KhimeraTestBase` and the option presets. It must not import the client package.

Conventions the suite follows, and new tests should too:

- Every assertion carries a message saying what triggered it, usually the option combination
  (`option_description()`), so a failure explains itself without a debugger.
- Tables of expected values are deliberate tripwires: `EXPECTED_COUNTS` and `EXPECTED_OPTION_KEYS`
  in `generation/test_options.py`, `EXPECTED_RULE_LOCATIONS` in `generation/test_locations.py`.
  An intended change to the world updates the table in the same change.
- There is no expected-failure mechanism. A red test is either a bug or a table to update.
- Two groups skip rather than fail when their input is missing: the patcher tests that need
  `patches/data.py` (run a build first) and the mod field parity check (needs the
  `KhimeraDAMG-AP-Mod` submodule checked out).
- The tests import Archipelago's own `test` package (`test.bases`, `test.general`, `test.param`),
  which a player's installation does not have. That is one more reason the package is
  apignored, and the packaging guard checks that it stays so.
- The code style below applies to the tests as to the rest of the apworld; `run_ruff.ps1`
  lints them.

`-Core` runs the core suite against the source through the junction, which is quick and catches
logic problems. The index requirement is about the built `.apworld`; see "Hard requirements for
inclusion" for that check.

### Four places carry a version

`APWORLD_VERSION` in `worlds/khimera_damg/__init__.py` goes into slot data, reaches the client
as the world version, and selects the communication agent. `world_version` in
`worlds/khimera_damg/archipelago.json` is what Archipelago reads and shows to players. They are
separate values with no code keeping them in step, so when they disagree, say so rather than
assuming either one is authoritative.

Two more live in `worlds/khimera_damg/client/patcher.py`, and a version bump has to touch them
too:

- `apworld_to_mod_map` maps each host apworld version to the highest mod version it works with.
  `max_apworld` is derived from its largest key, so a new `APWORLD_VERSION` with no entry here
  makes `_get_mod_version` raise "host apworld is too high". The client then cannot launch games
  for its own version, and start-up fails as soon as it looks up a source build.
- `min_apworld` is a hand-set floor. Its comment says to set it to `(0, 1, 0)` on the first
  release and leave it there afterwards.

If the bump also needs a new mod release, that version has to be listed in
`worlds/khimera_damg/patches/include.txt` as well, or the build will not package its patches.

### Third-party packages

Prefer packages listed in `Archipelago/requirements.txt`. Those are the ones Archipelago
commits to shipping, and the only ones whose presence is a promise rather than a side effect.

A package that is present but *not* in that file is an indirect requirement: it arrives because
something else asked for it. Using one is allowed — sometimes it is the only thing that does
the job — but say so when it comes up, and name the chain it depends on and what breaks if that
chain changes. Do not quietly treat an indirect requirement as though it were guaranteed, and
do not refuse to use one either.

`psutil` is the current example, and the decision on it is already made. It is shipped with
Archipelago but absent from `requirements.txt`; it reaches the environment through
`Archipelago/worlds/_sc2common/requirements.txt` asking for `portpicker`, which in turn
requires psutil. The client uses it anyway, because `Process.create_time()` is what makes
identifying a launched game process exact and `pymem` — a direct requirement — has no
equivalent. If an Archipelago release ever ships without psutil, the agreed fallback is to
check only the pid and the executable name, accepting the rare misidentification that follows.
This is recorded in full under "Latent" in `docs/Known Issues.md`; read that entry before
reopening the question.

## Code style

All Python in `worlds/khimera_damg/` must follow the Archipelago style guide
(`Archipelago/docs/style.md`). **Check these on every review and before writing new code:**

- **120 characters per line**.
- **No trailing whitespace** on any line.
- **Double quotes** for all strings. Use f-strings over concatenation, with single
  quotes inside them: `f"Like {dct['key']}"`.
- **Space after `:` in annotations**: `regions: dict[str, Region]`, not `regions:dict[str, Region]`.
- **New-style type annotations**: `dict[str, int]`, `list[str]`, `str | None` — never
  `Dict`, `List`, `Tuple`, `Optional`, `Union` from `typing`.
- **Annotate all function signatures**, including return types (`-> None` when it returns nothing).
- **Closing brackets** line up with the start of the line that opened them:
  ```python
  stuff = {
      x: y
      for x, y in thing
  }
  ```
- PEP8 otherwise: `is not None` (not `not ... is None`), two blank lines between
  top-level definitions, no shadowing builtins (`id`, `type`, `map`), no unused imports.
- Avoid `match` statements unless they genuinely pattern-match.

In addition to these, the developer also adopted a few of their own rules to follow. The archipelago 
rules plus the new ones can be found in the `ruff.toml` file at the repo root. Note that it is stricter 
than the one in `Archipelago`, and should be the one used for linting. 

You may lint locally using `scripts/run_ruff.ps1`, or directly:
`ruff check --config ruff.toml worlds/khimera_damg/`

Do not use the `--fix` flag when running ruff (or `-Fix` when running `run_ruff.ps1`). This counts as a write for the purposes of ground rule 1.

Any usage of ruff rule skipping comments such as `# noqa` and `# ruff: disable[]` or
`# ruff: enable[]` is to be viewed as a deliberate choice by the user to go against
the style rules, and should be allowed.

**The standards above apply only to code *within* the apworld**, which includes
`worlds/khimera_damg/tests/`. Scratch tests under `testing/` do not need to meet them.

## Archipelago correctness rules

These cause real bugs, not just style complaints:

- **Never use the global `random` module.** Use `world.random` / `self.random` — seeds
  must be reproducible.
- **Item and location IDs must stay stable across releases.** Never renumber or reorder
  existing entries; append new ones. IDs must be > 0 and < 2**53.
- **Item/location names must not be purely numeric** and must be unique within their own table.
- **Option field names are the player-facing YAML keys.** Renaming one breaks existing
  player YAMLs — treat them as a released API.
- Read options into instance attributes in `generate_early`, not inside access-rule
  lambdas (rules are called thousands of times).
- Watch for late-binding closures when building rules in a loop — bind loop variables
  as default arguments.
- The item pool and the fillable location count must match. `get_filler_item_name` must
  return a *repeatable* item, never a unique one.
- Placements must agree in both directions: if item A sits on location A, `item.location` and
  `location.item` must point at each other.
- Do not change item or location placements from an output or stage step.

Several of these are enforced by the fuzzer used to gate index inclusion; see
"Distribution target: the ionium index" below.

## Distribution target: the ionium index

The apworld is meant to be submitted to the ionium index
(<https://github.com/ionium-ap/Archipelago-index>) once a stable 0.1.0 exists. The criteria
below are acceptance requirements for that release, not style preferences.

The index's own README opens with "Do **NOT** make demands of apworld authors to cater their
apworlds for inclusion in this index." That clause is aimed at third parties pestering other
developers to get their apworlds into the index. It does not apply here: the developer of this
apworld has chosen to submit it, so the index rules are this project's own requirements. Treat
them as a standing checklist, raise any violation you find, and report index readiness plainly.

### Hard requirements for inclusion

- **A stable public URL** — a GitHub release artifact or a direct link to the `.apworld`.
  Local sources (a file committed into the index repo) are no longer accepted.
- **The game is not banned on the Archipelago Discord** for copyright reasons. 
  - Khimera: Destroy All Monster Girls is not a banned game.
- **No large unknown executable binary blobs**, and no dependency on any.
  - The APWorld will host several small diff binary patches, which are allowed.
- **No use of remote resources during generation** — no update checks, no downloads, nothing
  that touches the network. This constrains generation only; the client's file transport and
  its network callbacks are a separate concern.
- **No ROM required to generate.** Worlds already in the index are exempt; new ones are not.
- **No forced interactivity during generation** — nothing that blocks waiting on input.
- **No obvious logic flaws** that make large multiworlds hard to generate. Direct use of the
  global `random` module is called out by name (see the correctness rules above), as are test
  failures "deemed problematic".
- **The world must pass all core unit tests.** Run Archipelago's own suite with the built
  `.apworld` in `custom_worlds/`: from the fuzzer worktree `fuzz-env/ap-fuzz`, after
  `run_fuzzer.ps1` has installed the fresh build, run
  `.venv\Scripts\python.exe -B -m unittest discover -s test/general -t .` (about 90 seconds, every
  world). The `-t .` is required: without it unittest imports the test modules as top-level
  modules instead of `test.general.*`, and nine of them fail to import whatever the world does.
  A failure there blocks inclusion on its own, separately from the fuzzer.
  `scripts/run_tests.ps1 -Core` is the quick source-tree version of the same suite, scoped to
  this world.
- **Generation failure rate below 1%**, measured with Eijebong's fuzzer, not counting
  `OptionError`s. It is measured with `empty-apworld` (<https://github.com/ionium-ap/empty-apworld>,
  100 free locations) present in the same multiworld, so that failures caused by a restrictive
  start are separated from real logic problems — anything still failing points at logic.
- **A beta of a core-verified game needs a distinct game name** (`LADX` -> `LADX beta`).
  Not applicable here.
- Failures occurring early, before `generate_basic`, may be excused, since YAML validation
  catches those cheaply and they cost little generation time.

### The fuzzer checks that count toward the 1%

Eijebong's fuzzer (<https://github.com/ionium-ap/Archipelago-fuzzer>) is a single `fuzz.py`
entry point plus a `hooks/` folder; each check below is one hook in that folder.

- `gerpocalypse` — Generic Entrance Randomization compatibility.
- `indirect_conditions` — entrance access rules that need `register_indirect_condition`.
- `item_location_count` — item pool size matches the fillable location count.
- `detect_rule_variable_capture_issues` — late-binding closures in rules built inside a loop.
- `check_placement_item_location_references` — `item.location` and `location.item` agree.
- `detect_output_placement_changes` — a world must not change placements in output/stage steps.

Each hook is written to run on its own, in a separate fuzzer pass. Its `reclassify_outcome` turns
every outcome it is not testing into a success (or an `OptionError`), so passing several hooks to
one run masks every failure, and a chained run reports 0 failures whatever the world does.
`gerpocalypse` also replaces `--with-static-worlds` with a Kingdom Hearts YAML, so the Empty slot
is dropped from any run it is loaded in. And `detect_output_placement_changes` wraps only
`generate_output`, so it never fires under `--skip-output`.

A failure rate is only meaningful from a pass with no checking hooks and the Empty world in every
generation. The fuzzer ships a `with_empty` hook for that (`hooks/with_empty.py`), which leaves
outcomes untouched: it
writes an Empty YAML and points `--with-static-worlds` at it. It loads `empty.apworld` from the
index's container paths, and otherwise relies on the world already being registered, which the
local setup provides through `custom_worlds/empty.apworld`.

Run at merge time and worth passing, but not counted toward the 1%:

- `determinism` — the same seed with the same YAMLs must produce the same result every run.
- Universal Tracker compatibility.

### Running the fuzzer

The workflow is established and scripted. `docs/Running the Fuzzer.md` is the full runbook; in
short, `scripts/run_fuzzer.ps1 -Setup` once, then `scripts/run_fuzzer.ps1 -Pass <pass>` per run.

It never writes inside `Archipelago/`: it fuzzes a detached git worktree of the submodule at
`fuzz-env/ap-fuzz` and clones the fuzzer itself into `fuzzer/`, both gitignored. Each run builds
a real `.apworld` through `scripts/build_apworld.ps1` and drops it into that worktree's
`custom_worlds/`, because a directory link there is not importable — only `.apworld` zips get
registered by Archipelago's meta-path finder.

Before every run (and during `-Setup`), `Sync-FuzzWorktree` in `run_fuzzer.ps1` checks the
worktree against the commit the `Archipelago` submodule has checked out. If they differ it checks
the worktree out at the submodule's commit, reinstalls the worktree's requirements into its venv
and rebuilds `empty.apworld`, so the apworld is always fuzzed on the core it was built against.
The two share the submodule's object store, so nothing is fetched. It refuses, and the run stops,
if the worktree has changes to tracked files. Creating or moving that worktree changes git state
in it, but never in `Archipelago/` itself.

The script runs one `fuzz.py` invocation per pass, following the rules above, through
`scripts/fuzzer/run_fuzz_pass.ps1`, which holds the pass table:

- `rate` (the default) — no checking hook, output not skipped, Empty in every generation through
  `with_empty`. The only pass whose numbers are the index's failure rate; it fails at 1% or more.
- One pass per counted hook, named after it, each loading that hook alone (plus `with_empty`,
  except `gerpocalypse`). `detect_output_placement_changes` runs without `--skip-output`; the
  others skip it. Any failure in a check pass is a finding.
- `determinism`, with half the jobs and twice the timeout. `checks` runs the six counted passes,
  `all` runs `rate` then `checks`.
- `canary` — builds a world that is broken on purpose (`scripts/fuzzer/build_canary_apworld.ps1`),
  expects the `rate` and `item_location_count` passes over it to fail, and removes it afterwards.
  A canary that passes means the pipeline is hiding failures again.

Defaults: `-Runs 500 -Jobs 16 -Yamls 1 -Timeout 15`, with `fuzz-meta/khimera_damg.yaml` passed as
an absolute path unless `-NoMeta`. Each pass is archived to
`fuzz-env/ap-fuzz/fuzz_runs/<timestamp>/<pass>/` (command line, fuzz.py's own output, and a
`result.json`), with a `run.json` recording the apworld hash and the three commits involved. The
script exits non-zero when any pass is not `ok`. `fuzz.py` flags, for reference: `-r` generations
(mandatory), `-j` parallel jobs, `-g` world (repeatable), `-n` YAMLs per generation, `-t` timeout,
`-m` fuzz-meta file, `--hook module:class`, `--skip-output` stops before `generate_output`,
`--dump-ignored`, `--with-static-worlds`, `--max-tasks-per-child`, `--stall-timeout`. `fuzz.py`
itself writes to `fuzz-env/ap-fuzz/fuzz_output` and wipes it at the start of every run.

### Index entry format, for when 0.1.0 ships

One `index/khimera_damg.toml` in the index repo. `name` must match the game name exactly as it
appears in a player YAML. `home` should link to the Discord thread, else the GitHub repo.
Every key in `[versions]` must be valid semver even if the release itself is not. The preferred
form is a global `default_url` templated with `{{version}}` plus bare `"0.1.0" = {}` entries,
which only works if release tags are plain semver — worth deciding before the first tag. The
format also has optional keys (`display_name`, `tags`, `[releases]`,
`min_ap_version`/`max_ap_version`, `disabled`), and the README says entries under `[versions]`
must carry no extra keys; check it for the current list when writing the file.

Per-world option constraints keep the fuzzer from rolling invalid combinations. This repository
keeps its own copy at `fuzz-meta/khimera_damg.yaml` for local runs, passed with the fuzzer's
`-m` flag. It uses the same path the index expects, so it can be copied across if the index ever
needs one — but the index's copy is separate, and a change here has to be mirrored there.

The file holds an empty mapping under the quoted game name and no constraints. That key has to
stay: a file with no mapping at all loads as `None`, and the fuzzer crashes with
`'NoneType' object has no attribute 'get'` before any generation. `fuzz.py` runs from
`fuzz-env/ap-fuzz`, so a relative `fuzz-meta/...` path does not resolve there; `run_fuzzer.ps1`
passes the absolute path itself.

## Other information

### The communication contract

`docs/Communication Contract v1.md` is the governing specification for the client-to-game
interface: file names, JSON document shapes, state flags, and the consumption and ownership
policy. Treat it as authoritative over the code — where the two disagree, that is a bug in the
code unless the user says otherwise.

Two separate folders are involved at runtime, and they are easy to confuse. The message files
and state flags live in the game-side sandbox, `platformdirs.user_data_dir("khimera_ap")`. The
client's own persistent storage lives under `Utils.user_path("khimera_damg")`. Both are outside
this repository, so rule 4 applies before reading them.

### Nothing to be compatible with

This version of the apworld has not been published yet. There is no such thing as a
"compatibility breaking change" because there is nothing for the current version to
be compatible with yet. Assume every change made is a change to the first ever version of
the apworld, meaning compatibility checks aren't required yet. In particular, this suspends the
ID-stability rule above: renumbering items and locations is fine for now.

Compatibility rules will start being enforced once version 0.1.0 is properly released;
this section will be removed by then.

### Task lists

The developer intends to focus on doing one thing at a time during development of the apworld.
Ideas for things unrelated to the current work are logged for future reference in
`docs/Future Reference.md`, and are worth bringing up once the user starts making changes in the
relevant section of the code.

There is also a todo list at the root of the repository. These are tasks the user knows need
doing but is leaving for another session. You do not need to raise them, but the information can
be useful as context for questions or code review.

The todo list focuses on tasks relevant to the current work, while the future reference list is
intended to store ideas and changes that are not relevant to the current work and would need
their own pull request. Neither is an exhaustive list of what to do — just things the developer
thought of while working on something else.

### The known-issues log

`docs/Known Issues.md` records problems that are known and accepted rather than fixed. It is
not a task list: an entry there is a decision to live with something, so read it before
re-raising a problem it already covers. Two sections:

- **Live** — happening now; someone running the current code can hit it.
- **Latent** — not happening now, but a change outside this repository would trigger it. The
  point of the entry is that the trigger gets recognised when it arrives.

When asked to log an issue, append it to the right section in this shape:

```markdown
## <Title>: <a small sentence describing the symptom, and how it relates to the cause if known>
### Cause:
What causes it, or "Unknown" if it is not known.
### Description:
What is actually observed, and — for a latent issue — what the accepted fallback is.
```

The title line carries both the name and the one-sentence symptom, so it reads on its own in a
table of contents. Keep the `### Cause:` section before `### Description:`, including when the
cause is unknown; an entry with no cause section is incomplete rather than concise. When the
last entry leaves a section empty, say so in a sentence rather than deleting the heading.
