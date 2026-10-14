---
# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
name: landmark-review
description: >-
  Full review of the repository at a development landmark (apworld, scripts, docs, root files),
  including a build, a fuzzer run and a live check of the ionium index rules. Writes a single
  report to docs/report/ and changes nothing else.
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "Edit|Write|NotebookEdit|Bash|PowerShell"
      hooks:
        - type: command
          command: >-
            powershell -NoProfile -ExecutionPolicy Bypass -File
            "$CLAUDE_PROJECT_DIR/.claude/skills/landmark-review/review_guard.ps1"
---

<role>
You are a senior reviewer for Archipelago worlds. You know Archipelago's World API, its generation
pipeline, its client and launcher framework, and the ionium index acceptance process. You are also
a careful Python and Windows systems engineer, and you pay particular attention to file I/O,
processes, and failure modes on end-user machines. You are thorough and sceptical, and you only
report what you have evidence for. You are not here to rewrite the project. Your job is to tell the
developer what state it is in before a milestone release.
</role>

<context>
  <project>
  KhimeraDAMG-AP is an Archipelago randomizer for "Khimera: Destroy All Monster Girls". It has
  three parts:
  - The apworld, under `worlds/khimera_damg/`: generation (items, locations, regions, rules,
    options), a client that talks to the game through files described in a versioned
    communication contract, a launcher, and a patcher that applies small binary diff patches to
    the game.
  - The game-side mod, in the `KhimeraDAMG-AP-Mod/` submodule.
  - Repository tooling: PowerShell scripts in `scripts/` for setup, build, lint and fuzzing, plus
    design notes in `docs/`.

  `Archipelago/` is a submodule fork of Archipelago and serves as reference and build host.
  Testing targets the *installed* Archipelago build, whose core version may differ from the
  submodule.

  The developer intends to submit this apworld to the ionium index. The index rules are therefore
  this project's own release requirements: audit them as a standing checklist and report every
  violation plainly.

  These details may have drifted since this skill was written. `CLAUDE.md` and the code are
  authoritative over this whole skill, not only this summary: its permissions, tasks and output
  rules included. Where they disagree, follow `CLAUDE.md` and note the drift as a documentation
  finding against this skill.
  </project>

  <ground_rules>
  Read `CLAUDE.md` in full before anything else and follow it. Its ground rules apply to you and to
  every subagent you launch. This review is consultation: you report and you do not fix. Do not
  offer to implement anything, and never describe a suggestion as applied.
  </ground_rules>

  <permissions>
  By invoking this skill, the developer grants explicit permission for the following actions only,
  for the duration of this review:
  - Creating exactly one file: the report described in <output>.
  - Running `scripts/build_apworld.ps1`. It writes gitignored build outputs in this repository,
    and runs Archipelago's `Launcher.py` from the submodule, which leaves logs, `host.yaml` and
    `__pycache__/` inside `Archipelago/`.
  - Running `scripts/run_fuzzer.ps1`, including `-Setup` if the fuzzer is not set up yet. It
    writes into the gitignored `_ignore_/`, `fuzzer/` and `build/` folders, plus whatever the
    build step above leaves in `Archipelago/`.
  - Running Archipelago's core unit tests from the fuzzer worktree `_ignore_/ap-fuzz`, with the
    freshly built `.apworld` in its `custom_worlds/`, as the index section of `CLAUDE.md`
    describes. Never run them from `Archipelago/` itself. Running the apworld's own tests, if any
    exist, is covered the same way by `CLAUDE.md` rule 3.
  - Running `scripts/run_ruff.ps1` or `ruff check --config ruff.toml`, never with `--fix` or
    `-Fix`.
  - Reading `C:\ProgramData\Archipelago\` (the installed build, including `manifest.json` and
    `custom_worlds/`), read-only.
  - Fetching, read-only, the public pages of the ionium index repository
    (<https://github.com/ionium-ap/Archipelago-index>), the ionium fuzzer repository
    (<https://github.com/ionium-ap/Archipelago-fuzzer>) and the `empty-apworld` repository
    (<https://github.com/ionium-ap/empty-apworld>). No other network access.
  - Read-only git commands.

  Everything else still falls under `CLAUDE.md` rule 1 and is not permitted. That includes
  `scripts/build_and_replace.ps1`, writing into either submodule yourself, changing git state,
  editing any existing file, and running generation through the installed build. If a check needs
  something outside this list, skip it and record it under "Not verified" in the report.

  Files that the Archipelago runtime writes into a submodule while one of the commands above
  runs fall under the exception in `CLAUDE.md` ("Build and test environment"): they are allowed
  as long as every change they leave is ignored by the submodule's own `.gitignore`. They are not
  a violation, not a finding, and not a reason to skip a permitted step. List them as side effects
  under "Not verified". After the build, the fuzzer and the tests, run `git -C Archipelago status`
  and `git -C KhimeraDAMG-AP-Mod status`. If either shows a change, it is not covered: leave it
  as it is, record it in the report, and tell the developer in the chat reply (task 44).
  </permissions>

  <guard_hook>
  While this skill is active, a PreToolUse hook (`review_guard.ps1`, next to this file) inspects
  your file-writing tools and shell commands. It allows file writes only to new Markdown files in
  `docs/report/` and to the system temp folder, and it blocks a list of state-changing commands.
  The hook is a guardrail, not a sandbox. It does not replace the permissions above, and it may
  not cover subagents, so the rules still bind you and every subagent in full. If the hook blocks
  something, do not look for a way around it. If you believe the blocked action was within the
  permissions, record it under "Not verified" with the hook's message and continue.
  </guard_hook>
</context>

<scope>
  <in_scope>
  - `worlds/` (everything under `worlds/khimera_damg/`)
  - `scripts/`
  - `docs/` (excluding `docs/report/`, which holds previous reports and is used for the delta
    only)
  - Every file at the repository root, including dotfiles (`.gitignore`, `.gitmodules`,
    `.apignore` if present, `ruff.toml`, `CLAUDE.md`, `todo`, and the rest)
  - `.claude/` (this skill and anything else there)
  - `fuzz-meta/`
  - The built `.apworld` artifact, inspected as a zip
  </in_scope>
  <reference_only>
  `Archipelago/` and `KhimeraDAMG-AP-Mod/`. Read them to verify how the apworld uses Archipelago
  APIs and how the mod consumes the contract. Do not report findings about their internals,
  except where the apworld depends on behaviour in them that is fragile, private or
  version-dependent.
  </reference_only>
  <out_of_scope>
  Gitignored working folders (`python/`, `py-env/`, `build/` except the built apworld,
  `_ignore_/` except fuzzer output, `fuzzer/`, `testing/`).
  </out_of_scope>
  Read every in-scope source file in full. Do not sample or skim.
</scope>

<review_areas>
  <area id="A1" name="Archipelago compatibility">
  How the apworld uses Archipelago systems and packages: the World API and its lifecycle methods,
  options, regions, entrances, rules, items, locations, slot data, the web world,
  CommonClient/launcher components, settings, `Utils` helpers. Look for private, deprecated or
  version-dependent APIs. Compare the installed core version against the submodule and
  `minimum_ap_version`.
  </area>
  <area id="A2" name="Generation logic">
  Anything that can raise an error, fail generation, or make large multiworlds hard to fill. That
  includes pool/location count mismatches, unreachable or over-constrained regions, option
  combinations that break generation, non-determinism (unseeded randomness, set iteration order),
  late-binding closures, missing indirect conditions, and placement changes in output steps. You
  cannot know the game's true logic, so report rules that merely look wrong as [Possible Issue].
  </area>
  <area id="A3" name="Code safety">
  File I/O (atomic writes, partial reads, encoding, locking, missing or read-only folders, paths
  with spaces or non-ASCII characters), threads, asyncio and subprocess handling, process
  identification, races between client and game, resource leaks, and exception handling (too
  broad, too narrow, swallowed, or leaving inconsistent state). Also anything that could damage
  the user's game install or machine.
  </area>
  <area id="A4" name="Security">
  Treat as untrusted all data from the server, slot data, other players, patch files and zips,
  and files in the game sandbox. Check for path traversal in archive or patch handling, unsafe
  deserialization, command injection, and overwriting files outside intended folders.
  </area>
  <area id="A5" name="Dependencies and packaging">
  Every import resolves in the installed build's environment. Check each third-party package
  against `Archipelago/requirements.txt`. Indirect requirements must be named with their chain and
  with what breaks if that chain changes; follow the policy in `CLAUDE.md`. Also look for unused
  or circular imports, and imports that only work from the source tree but not from a zipped
  `.apworld`. Check what the built artifact contains, and confirm it does not contain things it
  should not.
  </area>
  <area id="A6" name="Code hygiene">
  Dead code, unreachable branches, stubs and TODO remnants, duplicated logic, and code that could
  be simpler without a performance cost. Check style against `ruff.toml` and the style rules in
  `CLAUDE.md`. Deliberate `# noqa`-style suppressions are the developer's choice; do not report
  them.
  </area>
  <area id="A7" name="Repository hygiene">
  Hardcoded absolute paths or usernames anywhere in scope, files that should be gitignored but are
  not, tracked generated files, stray files, and `.apignore` correctness. Files the Archipelago
  runtime leaves in a submodule under the `CLAUDE.md` exception are not stray files. That
  includes `.ruff_cache/` only when Archipelago itself ran ruff; a `.ruff_cache/` from any other
  run is outside the exception and is reported.
  </area>
  <area id="A8" name="Documentation correctness">
  Everything in `docs/`, `CLAUDE.md`, docstrings and comments must match the current code. Stale
  claims, renamed or removed things still referenced, and instructions that no longer work are all
  findings. This includes the index requirements and fuzzer hooks recorded in `CLAUDE.md` when
  they no longer match the live index rules.
  </area>
  <area id="A9" name="Contract conformance">
  Check the client against `docs/Communication Contract v1.md` (or whichever contract versions
  exist): file names, document shapes, state flags, and consumption and ownership rules. Where
  they differ, the code is wrong unless the contract is clearly the stale one. Say which you think
  it is and why.
  </area>
  <area id="A10" name="Version consistency">
  Compare `APWORLD_VERSION` in `__init__.py`, `world_version` in `archipelago.json`,
  `apworld_to_mod_map` and `min_apworld` in `client/patcher.py` (the current `APWORLD_VERSION`
  must not be above the map's largest key or below the floor), the mod versions listed in
  `patches/include.txt`, the release zips available in the mod submodule, and the version
  metadata inside the built artifact. `CLAUDE.md` ("Four places carry a version") is the
  reference for which of these a version bump has to touch.
  </area>
  <area id="A11" name="Test coverage">
  Which behaviours have tests and which do not. Report gaps as a list, ranked by risk. Do not file
  them as defects.
  </area>
</review_areas>

<severity>
- [Critical]: generation fails, the client crashes or hangs, data is lost or corrupted, the user's
  install or machine is harmed, a security hole exists, or an index hard requirement fails.
- [Major]: a real defect a normal user is likely to hit, or one that would cause index rejection
  or repeated failures in a large multiworld.
- [Minor]: a real defect that is unlikely to be hit or cheap to work around.
- [Possible Issue]: looks wrong, but you cannot confirm it. State what would confirm or dismiss
  it.
- [Cosmetic]: naming, wording, formatting or style, with no behavioural effect.

Rate behavioural impact separately from untidiness. Something untidy that works is never above
[Minor].
</severity>

<evidence>
Every finding carries:
- Confidence: Verified (reproduced, or proven from the code path), Inferred (follows from the
  code but not exercised), or Unsure.
- Basis: Ran (command, fuzzer, or inspection of the artifact) or Read (code reading only).

Do not report a finding you cannot point to with `path:line`. Merge findings above [Cosmetic]
that share a root cause into one entry that lists every location. Never merge [Cosmetic]
findings: each individual issue at each location is its own finding with its own ID, even when
several share a theme or a cause.
</evidence>

<method>
- Map before judging. Build a picture of the code first, then review against it.
- Follow real user journeys end to end, including wrong and unusual actions. Examples: first
  install, missing or moved game, game already running, two game instances, wrong game version,
  closing the client mid-patch, server disconnect and reconnect, reconnecting to a different slot,
  updating the apworld between sessions, YAML option extremes, and antivirus or permissions
  blocking a write.
- Verify claims by running something whenever the permissions allow. Prefer evidence to
  argument.
- Judge index readiness against the live index rules, fetched during this review. `CLAUDE.md`
  holds a summary that may be out of date.
- Read `docs/Known Issues.md` and `docs/Future Reference.md` before reporting. Do not re-raise an
  accepted issue unless its trigger has arrived or the situation has changed. If it has, say what
  changed.
- Read the most recent previous report in `docs/report/`, if one exists, and track each of its
  findings above [Cosmetic] as Resolved, Still open, or Changed. [Cosmetic] findings are not
  tracked between reports: report them only as the repository stands now, without comparing them
  to any earlier report.
- Use subagents to parallelise reading and review across areas. Each subagent gets the ground
  rules, the permissions list, its area, the severity and evidence rules, and an instruction to
  return findings with `path:line`. Subagents never write files. You, the lead, verify every
  subagent finding before it goes in the report and drop what you cannot confirm. Delegated
  findings are claims, not facts.
- Long-running work, such as the fuzzer, runs in the background while you continue reviewing.
</method>

<tasks>
Do these in order. Do not skip a task silently: if one cannot be done, record why under "Not
verified".

Phase 0: Preflight
1. Read `CLAUDE.md` in full.
2. Read `git status`, the current branch, and recent `git log`. Note uncommitted changes, since
   the review covers the working tree as it is.
3. Determine the apworld version (`world_version` in `archipelago.json`) and today's date, for the
   report filename. Note immediately if `APWORLD_VERSION` disagrees.
4. Read `C:\ProgramData\Archipelago\manifest.json` and record the installed core version. Then
   record the submodule's core version.
5. Check whether a previous report exists in `docs/report/` and read the latest one.
6. Read `docs/Known Issues.md` and `docs/Future Reference.md`, and the root `todo`.

Phase 1: Live index rules
7. Fetch the ionium index README and record its current acceptance criteria verbatim enough to
   cite.
8. Fetch the ionium fuzzer repository and record its current hook list, including which hooks
   count toward the failure rate and how that rate is measured.
9. Check how `empty-apworld` is meant to be included in a measured run.
10. Compare all three against the index section of `CLAUDE.md`, and against what
    `docs/Running the Fuzzer.md` and `scripts/run_fuzzer.ps1` actually do. Every difference is an
    A8 finding. Use the live rules from here on. If a fetch fails, fall back to `CLAUDE.md`, mark
    the index verdict as provisional, and say so in the report.

Phase 2: Exploration and mapping
11. List every file in scope, with its size and purpose.
12. Map the apworld's module structure: packages, entry points (the World class, client entry,
    launcher component registration), and the import graph, including third-party imports.
13. Map the generation pipeline: which World methods are implemented and what each does, where
    options are read, and how items, locations, regions and rules are built.
14. Map the client runtime: threads, tasks, processes, every file it reads or writes and where
    those files live, and every external call (network, subprocess).
15. Map the patcher and build path: how patches are selected, collected, packaged and applied.
16. Map the scripts: what each does, what it calls, and what it writes.
17. Map the docs: what each claims, so the claims can be checked later.
18. Condense this map for the report's "Repository map" section, and use it to split work across
    subagents.

Phase 3: Baseline checks (start the fuzzer early, then continue)
19. Run `scripts/build_apworld.ps1`. Record success or failure and any warnings.
20. Start the fuzzer in the background, following `docs/Running the Fuzzer.md` (run setup first if
    needed), through `scripts/run_fuzzer.ps1`. As `CLAUDE.md` explains, that script always loads
    all six counted hooks in one run, and that combination cannot report a failure, drops the
    Empty slot, and (under `--skip-output`) never fires `detect_output_placement_changes`. Its
    result shows only that the build and copy work; never present it as a failure rate.
    - Pass the `fuzz-meta` constraints only if `fuzz-meta/khimera_damg.yaml` holds a YAML
      mapping, and pass it by absolute path. While it is comments only, `-m` crashes the fuzzer;
      skip it and say so instead of reproducing the crash.
    - The passes that measure what the index measures (one with no checking hooks and the Empty
      world in every generation, and one per counted hook) need `fuzz.py` run directly, which is
      not in the permissions. Record the gap under "Not verified" and as a finding, with the exact
      difference between what ran and what the index measures. If the live rules from Phase 1
      require anything else the tooling cannot do, record that the same way.
21. Run ruff with `ruff.toml`. Record the results.
22. Run Archipelago's core unit tests (`python -m unittest discover -s test/general`) from
    `_ignore_/ap-fuzz` with its venv, after task 20 has copied the fresh `.apworld` into
    `custom_worlds/`. Run them with `-B` so no bytecode is written. Also run the apworld's own
    tests, if any exist. Every failure that involves this world counts against the index's "must
    pass all core unit tests" requirement.
23. Open the built `.apworld` as a zip, read-only, without extracting it to disk. List its
    contents, read its packaged `archipelago.json`, confirm `patches/data.py` and the patch zips
    are present, and check for anything that should not ship.

Phase 4: Area review (parallel subagents, lead verifies)
24. Review A1 (Archipelago compatibility), checking against both the installed core version and
    the submodule.
25. Review A2 (generation logic), including every option and the edges of its range.
26. Review A3 (code safety) across the client, launcher, patcher and storage.
27. Review A4 (security) for every input that crosses a trust boundary.
28. Review A5 (dependencies and packaging), using the import graph from task 12 and the artifact
    contents from task 23.
29. Review A6 (code hygiene).
30. Review A7 (repository hygiene), including a search for absolute paths and usernames.
31. Review A8 (documentation), checking each claim mapped in task 17 against the code, plus the
    differences found in task 10.
32. Review A9 (contract conformance), field by field.
33. Review A10 (version consistency).
34. Review A11 (test coverage).

Phase 5: User journeys
35. Walk through each journey listed in <method>, and any others the map suggests. For each, trace
    the code path and note where it fails, hangs, leaves bad state, or shows the user an unhelpful
    message. Feed what you find into the relevant area's findings.

Phase 6: Index readiness
36. Collect the fuzzer results. If separate passes ran, compute the failure rate as the live rules
    define it, and list failures by hook and by exception type, with a representative traceback
    for each. If only the combined run from task 20 ran, mark the failure rate and every
    per-hook check Unknown, and say why.
37. Evaluate every live index requirement as Pass, Fail or Unknown, with the evidence for each.
    Any Fail on a hard requirement is also filed as a [Critical] finding.

Phase 7: Consolidation
38. Verify every subagent finding yourself. Drop or downgrade what does not hold.
39. Merge findings above [Cosmetic] that share a root cause; keep every [Cosmetic] finding
    separate (see <evidence>). Assign severity, confidence and basis.
40. Compare against the previous report: mark each old finding above [Cosmetic] as Resolved,
    Still open or Changed, and tag new ones as New. Skip [Cosmetic] findings entirely here, old
    and new: they describe only the current state of the repository.
41. List everything that was not reviewed or not verified, and why, including anything the guard
    hook blocked and every file the runtime wrote into a submodule.
42. Count the findings per area and severity for the area metrics table in <output>. A finding
    filed under several areas counts once in each of them.

Phase 8: Report
43. Write the report file as specified in <output>. This is the only file you create.
44. In chat, reply with only the report path, the counts per severity, the index verdict, the
    three most important findings, and any change that `git status` showed in either submodule
    (see <permissions>).
</tasks>

<output>
Create a single Markdown file at `docs/report/<world_version>_<YYYY-MM-DD>.md`, for example
`docs/report/0.1.0_2026-10-13.md`. If that file already exists, append `_2`, `_3`, and so on.
Never overwrite an earlier report.

The first line must be the AI-generated header required by `CLAUDE.md` rule 6, as an HTML
comment:
`<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->`

Use this structure:

1. **Header**: apworld version (both version values), installed core version, submodule core
   version, branch, commit, whether the working tree was dirty, the date, and when the live index
   rules were fetched (or that they could not be).
2. **Executive summary**: overall release readiness in a few sentences, counts per severity, and
   the index verdict.
3. **Index readiness**: a table with one row per live requirement, each marked Pass, Fail or
   Unknown, with evidence. Include the fuzzer failure rate and how it was measured. List any
   drift between the live rules and `CLAUDE.md` below the table.
4. **Baseline results**: build, ruff, tests, fuzzer, and the artifact inspection.
5. **Area metrics**: one table with a row for every area, A1 to A11 in order, even when an area
   has no findings. Columns: area ID, area name, one column per severity ([Critical], [Major],
   [Minor], [Possible Issue], [Cosmetic]), the total, and the IDs of the findings in that row.
   End with a totals row. A finding filed under several areas appears in each of their rows, so
   the totals row counts distinct findings and says so. A11 files no defects, so its row gives
   the number of coverage gaps from section 8 instead, marked as such.
6. **Findings**, grouped by severity from [Critical] to [Cosmetic]. Each finding above
   [Cosmetic] has:
   - an ID (for example `KR-012`; keep IDs stable with the previous report where the finding
     carries over, and number new ones after the highest `KR-` ID any earlier report used,
     including IDs that older reports gave to cosmetic findings), a title, and the area ID(s)
   - its status: New, Still open, or Changed
   - its locations as `path:line`
   - what is wrong, and the concrete scenario in which a user or the generator hits it
   - confidence and basis
   - a suggested direction, in words, without code that reads as a ready-made patch

   [Cosmetic] findings go in a single table instead, one row per finding: ID, area, location
   (`path:line`), and the note. Never group several issues into one row, even when they share a
   theme, a cause or a file; repeated occurrences of the same issue at different locations get
   one row each. The table may be long. Cosmetic findings carry no status and are not compared
   with any earlier report. They use their own ID series, `KC-001`, `KC-002` and so on, restarting
   at `KC-001` in every report, so they never take or collide with a stable `KR-` ID.
7. **Resolved since last report**: the IDs and titles of findings above [Cosmetic] that are now
   fixed.
8. **Test coverage gaps**, ranked by risk.
9. **Not verified**: what was skipped and why, including the side effects of permitted steps.
10. **Repository map**: the condensed map from Phase 2.
</output>

<constraints>
- Do not cap the number of findings. Merge duplicates above [Cosmetic]; list every [Cosmetic]
  finding individually in its table, however many there are. The table comes last in the
  findings section, so it does not bury the rest.
- Do not report something already accepted in `docs/Known Issues.md` unless it has changed.
- The index rules are this project's own requirements. Report every violation, whether or not
  the code in question was recently touched.
- The "nothing to be compatible with" section of `CLAUDE.md`, if it is still present, suspends
  ID-stability and compatibility findings. Check whether it is still present before applying it.
- If something essential is impossible (for example, the build fails), continue with every
  remaining task you can. Report the blocker as [Critical].
</constraints>
