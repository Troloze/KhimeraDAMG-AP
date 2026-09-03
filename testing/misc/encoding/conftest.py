# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Loads ``worlds/khimera_damg/misc.py`` on its own.

``misc`` imports nothing but ``re`` and ``unicodedata``, so unlike the contract package it
can be loaded straight from its path -- no synthetic parent packages, no Archipelago
stubs. Keeping it standalone means these tests stay green even while the communication
package is mid-refactor.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MISC = REPO_ROOT / "worlds" / "khimera_damg" / "misc.py"


def _load_misc() -> ModuleType:
    spec = importlib.util.spec_from_file_location("khimera_misc", MISC)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {MISC}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["khimera_misc"] = module
    spec.loader.exec_module(module)
    return module


misc = _load_misc()


@pytest.fixture
def normalize() -> object:
    return misc.normalize_and_sanitize
