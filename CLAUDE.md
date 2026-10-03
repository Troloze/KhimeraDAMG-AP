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

- `worlds/khimera_damg/` — the apworld source (the thing being developed)
- `Archipelago/` — submodule, a fork of Archipelago. Read it freely; never modify it.
- `KhimeraDAMG-AP-Mod/` — submodule, the game-side mod. Same rule: read freely, never modify.
- `docs/` — design notes: the communication contract, item/location conventions, the option
  list, the fuzzer runbook, and the future-reference list.
- `scripts/` — PowerShell tooling. `scripts/setup/` and `scripts/build/` hold the steps the
  top-level scripts call. See "Build and test environment".
- `fuzz-meta/` — option constraints for local fuzzer runs.
- `todo` — tracked short-term task list; see "Task lists".

Gitignored working folders, present on a configured clone and never committed: `python/`
(standalone interpreter), `py-env/` (build venv), `build/` (apworld output), `_ignore_/`
(fuzzer worktree), `fuzzer/` (fuzzer clone), and `testing/` (scratch tests — this folder is to
stay gitignored permanently).

## Build and test environment

**Testing happens against the installed Archipelago build, not against the `Archipelago/`
submodule.** The submodule is a source for reading and the host the build runs through; it is
never modified.

**Do not create, edit, or delete anything inside `Archipelago/` or `KhimeraDAMG-AP-Mod/`** — no
generation output, no build folders, no installed dependencies. Rule 1 applies to both in full.
The pipeline below is deliberately arranged so that nothing is ever written into either.

### Fresh clone

    git submodule update --init --recursive
    scripts/setup.ps1

`scripts/setup.ps1` runs the three steps in `scripts/setup/`, in this order:

1. `setup_python.ps1` — installs CPython (3.13.15 by default) into `python/`, per-user and off
   PATH. Archipelago hard-rejects any interpreter outside 3.11.9–3.13.x.
2. `setup_world_link.ps1` — creates a junction at `Archipelago/worlds/khimera_damg` pointing at
   `worlds/khimera_damg`, and records it in the submodule's local `info/exclude` so it never
   shows up as untracked there. The link is what makes the apworld visible to Archipelago's own
   build component and to static analysis. It is a per-clone artifact, committed to neither
   repository, and it is the only thing that ever appears inside `Archipelago/`.
3. `setup_build_env.ps1` — creates a venv at `py-env/` and installs Archipelago's requirements
   into it using the submodule's own `ModuleUpdate.py`. Needs `git` on PATH, because some
   requirements are installed straight from GitHub.

Each step is idempotent and exits early if its output already exists; pass `-Force` to redo
them.

### Building

    scripts/build_apworld.ps1          # build only
    scripts/build_and_replace.ps1      # build, then install into the app folder

`build_apworld.ps1` first calls `scripts/build/collect_patches.ps1`, which copies the mod
releases named in `worlds/khimera_damg/patches/include.txt` out of
`KhimeraDAMG-AP-Mod/releases/` into `worlds/khimera_damg/patches/`. It then runs Archipelago's
own "Build APWorlds" launcher component from the repository root, producing
`build/apworlds/khimera_damg.apworld`.

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
- `scripts/run_ruff.ps1` lints the apworld. `scripts/run_fuzzer.ps1` runs the fuzzer; see
  "Running the fuzzer" below.
- Building, copying, and generating all write files. Propose the commands and wait to be
  asked, the same as any other change.

### Two places carry a version

`APWORLD_VERSION` in `worlds/khimera_damg/__init__.py` goes into slot data, reaches the client
as the world version, and selects the communication agent. `world_version` in
`worlds/khimera_damg/archipelago.json` is what Archipelago reads and shows to players. They are
separate values with no code keeping them in step, so when they disagree, say so rather than
assuming either one is authoritative.

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

Any usage of ruff rule skipping comments such as `# noqa` and `# ruff: disable[]` or
`# ruff: enable[]` is to be viewed as a deliberate choice by the user to go against
the style rules, and should be allowed.

**The standards above apply only to code *within* the apworld.** Scratch tests under
`testing/` do not need to meet them.

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
apworlds for inclusion in this index." Respect that: raise these points when reviewing code
that already touches the relevant area, not as a standing checklist to push on the developer.

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

Run at merge time and worth passing, but not counted toward the 1%:

- `determinism` — the same seed with the same YAMLs must produce the same result every run.
- Universal Tracker compatibility.

### Running the fuzzer

The workflow is established and scripted. `docs/Running the Fuzzer.md` is the full runbook; in
short, `scripts/run_fuzzer.ps1 -Setup` once, then `scripts/run_fuzzer.ps1` per run.

It never writes inside `Archipelago/`: it fuzzes a detached git worktree of the submodule under
`_ignore_/ap-fuzz` and clones the fuzzer itself into `fuzzer/`, both gitignored. Each run builds
a real `.apworld` through `scripts/build_apworld.ps1` and drops it into that worktree's
`custom_worlds/`, because a directory link there is not importable — only `.apworld` zips get
registered by Archipelago's meta-path finder.

Default invocation, for reference:
`fuzz.py -r 500 -j 16 -g khimera_damg -n 1` — `-r` generations (mandatory), `-j` parallel
jobs, `-g` world (repeatable), `-n` YAMLs per generation, `-t` timeout, `-m` fuzz-meta file,
`--hook module:class`. Output lands in `_ignore_/ap-fuzz/fuzz_output`.

### Index entry format, for when 0.1.0 ships

One `index/khimera_damg.toml` in the index repo. `name` must match the game name exactly as it
appears in a player YAML. `home` should link to the Discord thread, else the GitHub repo.
Every key in `[versions]` must be valid semver even if the release itself is not. The preferred
form is a global `default_url` templated with `{{version}}` plus bare `"0.1.0" = {}` entries,
which only works if release tags are plain semver — worth deciding before the first tag.

Per-world option constraints keep the fuzzer from rolling invalid combinations. This repository
keeps its own copy at `fuzz-meta/khimera_damg.yaml` for local runs, passed with the fuzzer's
`-m` flag. It uses the same path the index expects, so it can be copied across if the index ever
needs one — but the index's copy is separate, and a change here has to be mirrored there.

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
