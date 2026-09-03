# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""get_agent() maps an apworld version string onto a contract/agent pair.

The mapper no longer hands back a contract class -- it returns a zero-argument callable
that builds an agent already bound to the matching contract. These tests pin both halves:
the version resolution itself, and the fact that the callable produces a usable pairing.
"""

from __future__ import annotations

import pytest

from harness import AgentV1, CommunicationAgent, ContractV1, get_agent


@pytest.mark.parametrize("version", ["0.0.0", "0.0.2", "0.1.0", "1.0.0", "99.99.99"])
def test_versions_at_or_above_the_floor_resolve(version: str) -> None:
    assert callable(get_agent(version))


@pytest.mark.parametrize("version", ["", "0.0", "0.0.2.1", "x.y.z", "0.0.-1", "0..2"])
def test_malformed_versions_raise_value_error(version: str) -> None:
    with pytest.raises(ValueError):
        get_agent(version)


def test_error_messages_are_diagnosable() -> None:
    # A bare `raise ValueError` gives nothing to debug from in a client log.
    with pytest.raises(ValueError) as excinfo:
        get_agent("0.0")
    assert str(excinfo.value) != ""


def test_the_callable_builds_an_agent_bound_to_its_contract(sandbox: object) -> None:
    agent = get_agent("0.0.0")()
    assert isinstance(agent, AgentV1)
    assert isinstance(agent, CommunicationAgent)
    assert agent.contract is ContractV1


def test_each_call_builds_a_fresh_agent(sandbox: object) -> None:
    # Agents are single-use: opened once, closed once, never reopened. The mapper must
    # therefore hand out a factory, not a shared instance.
    factory = get_agent("0.0.0")
    assert factory() is not factory()
