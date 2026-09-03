<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->
# Communication contract tests

Standalone tests for `worlds/khimera_damg/game_communication.py`. They do **not** require
an Archipelago checkout, an installed AP build, or a copy of the game.

## Running

```
python -m pytest testing/communication_contract
```

or, from inside this folder, just `python -m pytest`.

Requires `pytest`. Nothing else outside the standard library except `platformdirs`, which
the module under test already imports.

## How the isolation works

`game_communication.py` imports `Utils`, `CommonClient` and `NetUtils` at runtime.
`_stubs/` supplies the handful of names that are actually used — `NetworkItem`,
`ClientStatus`, `async_start` — copied field-for-field from Archipelago so the tests
exercise the real shapes without pulling in the real package.

`harness.py` puts `_stubs/` on `sys.path` and then loads the module straight from its file
path as a **top-level** module. Loading it outside its package means the
`from .client import KhimeraDAMGContext` line never runs; it sits under `TYPE_CHECKING`
and is never evaluated at runtime anyway.

`harness.contract()` returns a fresh `ContractV1` with the module-level `unknown_*_set`
dedup caches cleared. Those caches are process-wide, so without the reset a warning
suppressed by one test would be invisible to the next.

## What each file covers

| file | covers |
|---|---|
| `test_wire_format.py` | every identifier's exact on-the-wire row, against `docs/Communication Contract v1.md` |
| `test_roundtrip.py` | `parse_events` -> `parse_message` is the identity, so the two dispatch tables cannot drift |
| `test_line_endings.py` | CRLF and LF documents, per the spec's "accept CRLF or LF" clause |
| `test_malformed_input.py` | truncated rows, non-numeric fields, blank lines, binary noise — the reader must not raise |
| `test_file_writers.py` | the per-file writers and the `write_content` / `read_content` facade |
| `test_subclassing.py` | whether `ContractV2(ContractV1)` can actually override behaviour |
| `test_versioning.py` | `get_contract()` version resolution |
| `test_sandbox_folder.py` | the GameMaker sandbox path |

## Design note

The tests assert the **specification**, not the current implementation. A failure means
the code and `docs/Communication Contract v1.md` disagree — which of the two is wrong is a
judgement call each time.
