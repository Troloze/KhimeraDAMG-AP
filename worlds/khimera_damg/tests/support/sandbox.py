# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Redirection of the two runtime folders the client writes to.

The client owns two directories outside this repository: its own storage under
``Utils.user_path("khimera_damg")`` and the game-side sandbox under
``platformdirs.user_data_dir("khimera_ap")``. Both hold real player data - save files, patched
builds, in-flight messages - and several code paths under test delete files in them.

Every client test therefore runs with both folders pointed at throwaway temporary directories,
and ``RedirectedTestCase`` asserts the redirection took effect before the test body runs. A test
that forgets a patch fails on that assertion instead of touching the real folders.
"""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

import Utils  # type: ignore

from ... import GAME_ID
from ...client.communication.contracts import ContractV1


@contextmanager
def temp_user_path() -> Iterator[Path]:
    """Point ``Utils.user_path`` at a temporary directory for the duration of the block.

    ``Utils.user_path`` memoises its root in a ``cached_path`` attribute on the function itself
    (``Archipelago/Utils.py``), so patching that attribute moves every caller at once, including
    ``KhimeraDAMGStorageHandler``. ``create=True`` is needed because the attribute may not exist
    yet; mock then removes it again on exit, restoring the original lazy behaviour.
    """
    with tempfile.TemporaryDirectory(prefix="kdamg_user_", ignore_cleanup_errors=True) as raw:
        root = Path(raw)
        with mock.patch.object(Utils.user_path, "cached_path", str(root), create=True):
            yield root


@contextmanager
def temp_sandbox() -> Iterator[Path]:
    """Point the contract's sandbox folder at a temporary directory for the duration of the block."""
    with tempfile.TemporaryDirectory(prefix="kdamg_sandbox_", ignore_cleanup_errors=True) as raw:
        root = Path(raw)
        with mock.patch.object(ContractV1, "get_sandbox_folder", classmethod(lambda _cls: root)):
            yield root


class RedirectedTestCase(unittest.TestCase):
    """Base for client tests: both runtime folders redirected, with a guard that proves it.

    ``outside_root`` is a third temporary directory that stands in for "somewhere else on the
    machine" - where an exported save lands, or where a decoy file is planted to show that a
    rejected path really was not written to.
    """

    user_root: Path
    sandbox_root: Path
    outside_root: Path

    def setUp(self) -> None:
        super().setUp()
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.user_root = stack.enter_context(temp_user_path())
        self.sandbox_root = stack.enter_context(temp_sandbox())
        self.outside_root = Path(
            stack.enter_context(tempfile.TemporaryDirectory(prefix="kdamg_outside_", ignore_cleanup_errors=True))
        )
        self.assert_paths_redirected()

    def assert_paths_redirected(self) -> None:
        storage = Path(Utils.user_path(GAME_ID)).resolve()
        user_root = self.user_root.resolve()
        self.assertTrue(
            storage.is_relative_to(user_root),
            f"client storage was not redirected: {storage} is outside the temporary root {user_root}. "
            "A test must never write to the real user folder."
        )
        sandbox = ContractV1.get_sandbox_folder().resolve()
        sandbox_root = self.sandbox_root.resolve()
        self.assertTrue(
            sandbox.is_relative_to(sandbox_root),
            f"the game sandbox was not redirected: {sandbox} is outside the temporary root {sandbox_root}. "
            "A test must never write to the real sandbox folder."
        )


class AsyncRedirectedTestCase(RedirectedTestCase, unittest.IsolatedAsyncioTestCase):
    """The same redirection for tests that need a running event loop.

    ``CommonContext.__init__`` creates its keep-alive task straight away, so a
    ``KhimeraDAMGContext`` can only be built inside a loop.
    """
