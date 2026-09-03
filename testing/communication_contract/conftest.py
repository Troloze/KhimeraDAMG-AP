# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Path setup, plus the sandbox redirection every agent test depends on.

``AgentV1.__init__`` calls ``test_sandbox_access``, which creates the sandbox directory
and writes a probe file into it. The real path is ``%LOCALAPPDATA%\\khimera_ap`` -- the one
a running game is using -- so construction has to be redirected before any agent exists,
not after. Patching ``get_sandbox_folder`` on the contract is the only hook that lands
early enough, since the agent reads it in its constructor.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every contract's sandbox at a scratch directory for this test."""
    from harness import ContractV1

    monkeypatch.setattr(ContractV1, "get_sandbox_folder", classmethod(lambda cls: tmp_path))
    return tmp_path


@pytest.fixture
def agent(sandbox: Path) -> Any:
    """A constructed, unopened AgentV1 bound to ContractV1 and the scratch sandbox."""
    from harness import get_agent

    return get_agent("0.0.0")()
