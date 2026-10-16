# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""A tripwire for Python version compatibility (KR-008).

Archipelago supports 3.11.9 through 3.13.x, and its own release workflows build on 3.12, so the
apworld has to run on 3.11. Ruff with ``target-version = "py311"`` catches *syntax* that is too
new; what it does not catch is a standard library API that only exists in a later version. The
client once depended on ``queue.ShutDown`` and ``Queue.shutdown()``, which are 3.13-only, and
every player on a 3.12 build lost all communication with the game.

This scan is a tripwire, not a proof: the only real check is running the suite on 3.11. Add a
name here whenever one of these bites again.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

WORLD_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = Path(__file__).resolve().parents[1]

MINIMUM_PYTHON = (3, 11)

# Names that only exist above MINIMUM_PYTHON, with the version that introduced them. These are
# unambiguous: no older API shares the name.
TOO_NEW_NAMES = {
    "ShutDown": "3.13 (queue.ShutDown)",
    "is_shutdown": "3.13 (queue.Queue.is_shutdown)",
    "batched": "3.12 (itertools.batched)",
    "override": "3.12 (typing.override)"
}

# ``shutdown`` is 3.13 only on a queue; on an executor, a loop or a context it is long-standing.
# It is therefore reported only when the receiver reads like a queue.
QUEUE_LIKE_RECEIVER = re.compile(r"(^|[._])(q|queue)s?$", re.IGNORECASE)


def world_sources() -> list[Path]:
    """Every shipped Python file in the apworld, excluding this test package."""
    return [
        path for path in sorted(WORLD_ROOT.rglob("*.py"))
        if not path.is_relative_to(TESTS_ROOT) and "__pycache__" not in path.parts
    ]


class TestSourcesParse(unittest.TestCase):
    """Every shipped file has to be valid Python."""

    def test_sources_were_found(self) -> None:
        sources = world_sources()
        self.assertGreater(len(sources), 5, f"only found {len(sources)} source files under {WORLD_ROOT}")

    def test_every_source_parses(self) -> None:
        for path in world_sources():
            with self.subTest(path=path.relative_to(WORLD_ROOT).as_posix()):
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                except SyntaxError as err:
                    self.fail(f"{path.relative_to(WORLD_ROOT).as_posix()} does not parse: {err}")


class TestNoTooNewApis(unittest.TestCase):
    """Attribute access and imports that would not exist on the oldest supported interpreter."""

    def location(self, path: Path, node: ast.AST) -> str:
        return f"{path.relative_to(WORLD_ROOT).as_posix()}:{node.lineno}"

    def test_no_shipped_source_uses_a_newer_api(self) -> None:
        offenders: list[str] = []
        for path in world_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                receiver = ast.unparse(node.value)
                if node.attr in TOO_NEW_NAMES:
                    offenders.append(
                        f"{self.location(path, node)} uses {receiver}.{node.attr}, which needs "
                        f"Python {TOO_NEW_NAMES[node.attr]}"
                    )
                elif node.attr == "shutdown" and QUEUE_LIKE_RECEIVER.search(receiver):
                    offenders.append(
                        f"{self.location(path, node)} uses {receiver}.shutdown(), which needs "
                        "Python 3.13 (queue.Queue.shutdown)"
                    )
        self.assertEqual(
            offenders,
            [],
            f"this apworld has to run on Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}:\n"
            + "\n".join(offenders)
        )

    def test_no_shipped_source_imports_a_newer_name(self) -> None:
        # from queue import ShutDown, from itertools import batched, and friends.
        offenders: list[str] = []
        for path in world_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                offenders.extend(
                    f"{self.location(path, node)} imports {alias.name} from {node.module}, "
                    f"which needs Python {TOO_NEW_NAMES[alias.name]}"
                    for alias in node.names
                    if alias.name in TOO_NEW_NAMES
                )
        self.assertEqual(
            offenders,
            [],
            f"this apworld has to run on Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}:\n"
            + "\n".join(offenders)
        )
