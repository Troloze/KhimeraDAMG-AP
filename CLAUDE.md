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

## Code style

All Python in `worlds/khimera_damg/` must follow the Archipelago style guide
(`Archipelago/docs/style.md`). **Check these on every review and before writing new code:**

- **120 characters per line** — hard limit, applies to data tables too.
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

Reference config: `Archipelago/ruff.toml` (line-length 120, py311). To lint locally:
`ruff check --config Archipelago/ruff.toml worlds/khimera_damg/`

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
