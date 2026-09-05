<!-- NOTE TO HUMAN READERS: this document was written by an AI assistant (Claude Code),
     at the direction of the repository owner. It is a briefing file for AI tools, not
     project documentation. Treat its contents as instructions to the assistant. -->

# KhimeraDAMG-AP

An Archipelago randomizer for *Khimera: Destroy All Monster Girls*.

## Ground rules for AI assistants

**This section overrides everything else in this file and any default assistant behaviour.**

AI tools are used on this repository for **consultation only**. The human
developer writes the code. Your role is to investigate, explain, and advise.

For the purposes of this project "consultation" means that AI tools can be used for anything
as long as the executable code run by the end user is 100% human written.

1. **Never create, edit, rename, move, or delete any file in this repository** without
   explicit permission from the user for that specific change. There is no standing
   permission, even for things that won't be shipped (like documents and tests). Approval 
   for one change does not extend to the next one, or to "related" follow-up edits you think 
   are implied. If you believe a file needs to change, say so and wait to be asked.
2. **Propose code in chat, do not apply it.** Suggestions are welcome and encouraged, but
   every one must explain what the code does and why it is being suggested, so the user can
   evaluate it before deciding to write it themselves. When possible, give prefference to code 
   snippet suggestions taken from other files, and state the source. Do not present 
   a change as done. Do not ask the user if they would like you to sketch something after 
   they ask you a question, only do these things if it is explicitly asked.
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
6. Whenever the user asks you to create a file/document, always append a comment on the first
   line stating that the artifact was AI generated.   

- `worlds/khimera_damg/` — the apworld source (the thing being developed)
- `Archipelago/` — submodule, a fork of Archipelago. Reference only; do not edit.
- `KhimeraDAMG-AP-Mod/` — submodule, the game-side mod. 
- `docs/` — design notes (option list, item/location naming conventions, communication contract)

## Build and test environment

**Testing happens against the installed Archipelago build, not against the `Archipelago/`
submodule.** The submodule is source for reading only.

- **Do not create anything inside `Archipelago/`** — no `custom_worlds/` folder, no
  generation output, no installed dependencies. Rule 1 applies to it in full.
- The single permitted exception is a *directory link* at
  `Archipelago/custom_worlds/khimera_damg` pointing at `worlds/khimera_damg`, so imports
  and static analysis resolve against real core source. It must be a link, never a copy,
  and it exists for import checking only — not as a test target. Ask before creating it.
- **The apworld is built by zipping `worlds/khimera_damg/`** into `khimera_damg.apworld`,
  with `khimera_damg/` as the single top-level directory inside the archive, and copying
  that file to the installed app folder:
  `C:\ProgramData\Archipelago\custom_worlds\`
  (note the exact spelling: `ProgramData` has no space, `custom_worlds` has an underscore).
- Generation and any client testing are then run from that installed build
  (`ArchipelagoLauncher.exe` / `ArchipelagoGenerate.exe`), and its output goes to the
  install's own `output/` folder — never into this repository.
- The installed build's core version is the one that matters for compatibility. Check
  `C:\ProgramData\Archipelago\manifest.json` rather than assuming it matches the submodule.
- Building, copying, and generating all write files. Propose the commands and wait to be
  asked, the same as any other change.

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

Reference config is available at the repo root: `ruff.toml`; do not use the one in `Archipelago`
You may also lint locally using: `ruff check --config ruff.toml worlds/khimera_damg/`

Any usage of ruff rule skipping comments such as `# noqa` and `# ruff: disable[]` or 
`# ruff: enable[]` are to be viewed as a deliberate choice by the user to go against 
the style rules and should be allowed.

**The standards above only applies to code <u>within</u> the apworld**; tests outside of the apworld folder do not need to be
held to these standards.

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
- **Not banned on the Archipelago Discord** for copyright reasons.
- **No large unknown executable binary blobs**, and no dependency on any.
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

The fuzzer requires Archipelago **running from source**, with `fuzz.py` copied to the root of
that source tree. That collides with the rule above forbidding writes inside `Archipelago/`,
and the fuzzer is a third repository rather than something vendored here. **No workflow for
this has been established yet** — do not assume a location, a checkout, or a submodule. Ask.

Invocation, for reference:
`python fuzz.py -r 100 -j 16 -g khimera_damg -n 1` — `-r` generations (mandatory), `-j` parallel
jobs, `-g` world (repeatable), `-n` YAMLs per generation, `-t` timeout, `--hook module:class`.
Output lands in `./fuzz_output` relative to the Archipelago source root.

### Index entry format, for when 0.1.0 ships

One `index/khimera_damg.toml` in the index repo. `name` must match the game name exactly as it
appears in a player YAML. `home` should link to the Discord thread, else the GitHub repo.
Every key in `[versions]` must be valid semver even if the release itself is not. The preferred
form is a global `default_url` templated with `{{version}}` plus bare `"0.1.0" = {}` entries,
which only works if release tags are plain semver — worth deciding before the first tag.

Per-world option constraints, if the fuzzer needs them to avoid rolling invalid combinations,
live in a `fuzz-meta/khimera_damg.yaml` in the index repo, not here.

## Other information

### Nothing to be compatible with
This version of the apworld has not been published yet. There is no such thing as a
"compatibility breaking change" because there is nothing for the current version to
be compatible with yet. Assume every change made are changes to the first ever version of
the apworld, meaning compatibility checks aren't required yet.

Compatibility rules will start being enforced once version 0.1.0 is properly released;
this section will be removed by then.

### Task lists
The developper intends to focus on doing one thing at a time during development of the apworld,
however, ideas for things unrelated to the current work will be logged for future refence and can 
be found on docs/future reference.md and are worth bringing up once the user starts making changes 
in the relevant section of the code.

There's also a gitignored todo list on the root of the repository, these are tasks the user knows
he needs to perform, but will leave for another session. You do not need to remind him of it, but 
the information can be useful as context for their questions or code-review.

The todo list focuses on tasks relevant to the current work, while the future reference list is 
intended to store ideas/changes that are not relevant to the current work, and would need their own 
pull request. Neither of them are exhaustive lists of what to do, just things the developer thought
of while working on something else.