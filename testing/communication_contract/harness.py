# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Loads the ``communication`` package out of worlds/khimera_damg without Archipelago.

``contracts/contract_v1.py`` reaches its siblings through package-relative imports
(``from ..classes import ...``), so it cannot be loaded as a lone file. Instead this
registers the world root as a synthetic package whose ``__path__`` points at the real
directory; everything below it is then imported for real, so the tests walk the same
import graph the apworld does. ``_stubs/`` supplies the handful of Archipelago names
that graph reaches for.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WORLD = REPO_ROOT / "worlds" / "khimera_damg"
STUBS = HERE / "_stubs"

#: The sole-dollar-sign row that terminates every document in contract v1.
TERMINATOR = "$"

if str(STUBS) not in sys.path:
    sys.path.insert(0, str(STUBS))


def _register_namespace(name: str, path: Path) -> None:
    """Put an empty package in sys.modules so the real modules below it can import."""
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module


# Only the world root is synthetic. Everything under communication/ is imported for real,
# so the tests exercise the same import graph the apworld does; _stubs/ supplies the
# Archipelago names (NetUtils, BaseClasses, rule_builder) that graph reaches for.
_register_namespace("khimera_world", WORLD)

classes_mod = importlib.import_module("khimera_world.communication.classes")
cv1 = importlib.import_module("khimera_world.communication.contracts.contract_v1")
av1 = importlib.import_module("khimera_world.communication.agents.agent_v1")
ct = importlib.import_module("khimera_world.communication.storage")
interface_mod = importlib.import_module("khimera_world.communication")
world_types = importlib.import_module("khimera_world.types")

CommunicationEvent = classes_mod.CommunicationEvent
CommunicationContract = classes_mod.CommunicationContract
CommunicationAgent = classes_mod.CommunicationAgent
ContractV1 = cv1.ContractV1
get_agent = ct.get_agent
AgentV1 = av1.AgentV1
Interface = interface_mod.KhimeraDAMGCommunicationInterface

ConnectionContext = world_types.ConnectionContext
LocationInformation = world_types.LocationInformation
RuntimeInformation = world_types.RuntimeInformation
RuntimeStatus = world_types.RuntimeStatus

# Serializer internals live at module level in contract_v1, not nested on the contract.
EventSerializer = cv1.EventSerializer
EventDeserializer = cv1.EventDeserializer
OptionSerializer = cv1.OptionSerializer
DataSerializer = cv1.DataSerializer

# The validators raise these instead of bare ValueError/TypeError, so the deserializers can
# tell a rejected field apart from an unrelated failure and drop just that row.
EventTypeError = classes_mod.EventTypeError
EventValueError = classes_mod.EventValueError

# Re-exported so test modules do not have to know about the _stubs directory.
NetworkItem = cv1.NetworkItem


def contract() -> type:
    """The contract class, with the module-level dedup caches cleared.

    Every contract method is a classmethod, so this returns the class rather than an
    instance. The ``unknown_*_set`` globals are process-wide, so without the reset a
    warning suppressed by one test would be invisible to the next.
    """
    cv1.unknown_event_set.clear()
    cv1.unknown_option_set.clear()
    cv1.unknown_data_set.clear()
    cv1.unknown_flag_set.clear()
    return ContractV1


# --- helpers for the (payload, exit_code) tuples the contract returns -------------

def text(result: tuple[str, int] | str) -> str:
    """The serialized document out of a writer result."""
    return result[0] if isinstance(result, tuple) else result


def code(result: tuple[Any, int]) -> int:
    """The exit code out of a writer or reader result."""
    return result[1]


def rows(result: tuple[str, int] | str) -> list[str]:
    """Content rows of a serialized document, with the trailing terminator removed."""
    out = [line for line in text(result).splitlines() if line != ""]
    if out and out[-1] == TERMINATOR:
        out.pop()
    return out


def raw_rows(result: tuple[str, int] | str) -> list[str]:
    """Every row of a serialized document, terminator included."""
    return text(result).splitlines()


def doc(*content_rows: str, terminated: bool = True, newline: str = "\n") -> str:
    """Build a document the way the game would write one."""
    body = [*content_rows, TERMINATOR] if terminated else list(content_rows)
    return newline.join(body)


#: The Event base class's three control flags. They are ``field``s, so they take part in
#: ``__eq__`` -- a deserialized event (built with ``sanitize_enabled=False``) is therefore
#: never ``==`` the same event constructed in client code. ``payload`` compares the fields
#: that actually carry wire data, so round-trip tests test the wire format rather than the
#: flag plumbing. ``test_event_identity.py`` pins the equality behaviour itself.
CONTROL_FLAGS = ("invalid", "validate_enabled", "sanitize_enabled")


def payload(event: Any) -> tuple[Any, ...]:
    """(type, *value fields) for one event, ignoring the control flags."""
    import dataclasses

    return (type(event), *(
        getattr(event, f.name)
        for f in dataclasses.fields(event)
        if f.name not in CONTROL_FLAGS
    ))


def payloads(events: list[Any]) -> list[tuple[Any, ...]]:
    return [payload(e) for e in events]


def normalised(value: str) -> str:
    """What ``normalize_and_sanitize`` makes of a string.

    Tests that care *which* policy a field follows use this rather than hard coding a
    transliteration, so they keep asserting the policy even while the normaliser's own
    character mapping is still being settled in ``testing/misc/encoding``.
    """
    import importlib

    misc = importlib.import_module("khimera_world.misc")
    return misc.normalize_and_sanitize(value)
