# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Stand-ins and builders used by the client tests.

Nothing here talks to a server, a game process or a thread. The agent built by ``make_agent``
is wired by hand instead of through ``open_communication``, so its tick methods can be called
one at a time and asserted on, which keeps the tests deterministic.
"""

from __future__ import annotations

import json
import queue
from pathlib import Path
from typing import Any

from NetUtils import NetworkItem  # type: ignore

from ...client.client import get_game_id
from ...client.communication.agents import AgentV1
from ...client.communication.classes import StopFlag
from ...client.communication.contracts import ContractV1
from ...client.types import ConnectionContext, LocationInformation


def make_item(item_id: int, player: int = 2, location: int = 100, flags: int = 0) -> NetworkItem:
    """A network item as the server would hand it to the client."""
    return NetworkItem(item_id, location, player, flags)


class FakeContext:
    """The parts of ``KhimeraDAMGContext`` that ``KhimeraDAMGConnectionState`` actually reads.

    The real context needs a running event loop and a websocket; the connection state only ever
    touches these three attributes, so the state can be tested on its own.
    """

    def __init__(
        self,
        game_id: str | None = "0123456789abcdef0123456789abcdef",
        checked_locations: set[int] | None = None,
        items_received: list[NetworkItem] | None = None
    ) -> None:
        self.game_id = game_id
        self.checked_locations: set[int] = checked_locations if checked_locations is not None else set()
        self.items_received: list[NetworkItem] = items_received if items_received is not None else []


def make_connection_context(**overrides: Any) -> ConnectionContext:
    """A valid connection context. Every field can be overridden by keyword.

    ``game_id`` defaults to the id the client would derive from the slot name and seed, so a
    context built here addresses the same save file the real one would.
    """
    params: dict[str, Any] = {
        "ap_version": "0.6.8",
        "host_world_version": "0.0.9",
        "client_world_version": "0.0.9",
        "slot_name": "Tester",
        "seed": "12345678901234567890",
        "last_ack": 0,
        "options": {},
        "generation_information": {},
        "game_data": {},
        "locations": set(),
        "item_list": [],
        "has_goaled": False
    }
    params.update(overrides)
    params.setdefault("game_id", get_game_id(params["slot_name"], params["seed"]))
    return ConnectionContext(**params)


def make_location_information(
    enabled: bool = True,
    loc_info: dict[int, tuple[int, int]] | None = None
) -> LocationInformation:
    """Location information, defaulting to an empty table."""
    return LocationInformation(enabled, loc_info if loc_info is not None else {})


def make_agent(
    *,
    context: ConnectionContext | None = None,
    location_information: LocationInformation | None = None
) -> tuple[AgentV1, queue.Queue, queue.Queue]:
    """Build an agent wired for single-threaded use.

    ``open_communication`` would start the consumer thread and run the cleanup step; the tests
    want neither, so the same attributes are set directly. Returns the agent plus its
    host-to-game and game-to-host queues.
    """
    agent = AgentV1(ContractV1)
    htg_q: queue.Queue = queue.Queue()
    gth_q: queue.Queue = queue.Queue()
    agent.htg_q = htg_q
    agent.gth_q = gth_q
    agent.s_flag = StopFlag()
    agent.connection_context = context if context is not None else make_connection_context()
    agent.location_information = (
        location_information if location_information is not None else make_location_information()
    )
    return (agent, htg_q, gth_q)


def drain(q: queue.Queue) -> list[tuple[str, Any]]:
    """Everything currently on a queue, in order."""
    items: list[tuple[str, Any]] = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            return items


def write_flag(sandbox: Path, flag: str, value: int) -> Path:
    """Create a state flag file the way the contract names them: ``<value>.<flag>``."""
    path = sandbox / f"{value}.{flag}"
    path.write_text("", encoding="ascii")
    return path


def clear_flags(sandbox: Path, flag: str) -> None:
    for path in sandbox.glob(f"*.{flag}"):
        path.unlink()


def game_message(**message: Any) -> str:
    """Wrap a dict the way the game writes ``ap.gi``: ``{"message": {...}}``."""
    return json.dumps({"message": message})
