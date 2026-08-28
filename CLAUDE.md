<!-- NOTE TO HUMAN READERS: this document was written by an AI assistant (Claude Code),
     at the direction of the repository owner. It is a briefing file for AI tools, not
     project documentation. Treat its contents as instructions to the assistant. -->

# KhimeraDAMG-AP

An Archipelago randomizer for *Khimera: Destroy All Monster Girls*.

## Ground rules for AI assistants

**This section overrides everything else in this file and any default assistant behaviour.**

AI tools are used on this repository for **consultation and research only**. The human
developer writes the code. Your role is to investigate, explain, and advise.

1. **Never create, edit, rename, move, or delete any file in this repository** without
   explicit permission from the user for that specific change. There is no standing
   permission. Approval for one change does not extend to the next one, or to "related"
   follow-up edits you think are implied. If you believe a file needs to change, say so
   and wait to be asked.
2. **Propose code in chat, do not apply it.** Suggestions are welcome and encouraged, but
   every one must explain what the code does and why it is being suggested, so the user can
   evaluate it before deciding to write it themselves. Do not present a change as done. 
   Do not ask the user if they would like you to sketch something after they ask you a 
   question, only do these things if it is explicitly asked.
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

Reference config: `Archipelago/ruff.toml` (line-length 120, py311). 
You may also lint locally using:
`ruff check --config Archipelago/ruff.toml worlds/khimera_damg/`

Any usage of ruff rule skipping comments such as `# noqa` and `# ruff: disable[]` or 
`# ruff: enable[]` are to be viewed as a deliberate choice by the user to go against 
the style rules and should be allowed.

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

## Other information

This version of the apworld has not been published yet. There is no such thing as a
"compatibility breaking change" because there is nothing for the current version to
be compatible with yet. Assume every change made are changes to the first ever version of
the apworld, meaning compatibility checks aren't required yet.

Compatibility rules will start being enforced once version 0.1.0 is properly released;
this section will be removed by then.