# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Contract: file communication happens in the GameMaker sandbox folder named khimera_ap."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from harness import contract


def test_sandbox_folder_is_absolute() -> None:
    assert contract().get_sandbox_folder().is_absolute()


@pytest.mark.skipif(os.name != "nt", reason="Khimera is a Windows-only game")
def test_sandbox_folder_is_localappdata_khimera_ap() -> None:
    expected = Path(os.environ["LOCALAPPDATA"]) / "khimera_ap"
    assert contract().get_sandbox_folder() == expected
