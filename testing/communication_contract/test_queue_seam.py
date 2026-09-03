# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The two queues, tested as a contract between a producer and a decoder.

Everything crossing between the client and the communication thread goes through a
``queue.Queue`` as a ``(tag, payload)`` tuple. Nothing type checks those tuples: the tag is
a bare string matched with ``==``, and each ``if`` in the decoder is independent, so an
unrecognised tag is not an error -- it is silently ignored. A producer and a decoder that
disagree therefore fail by *doing nothing*, with no exception and no log line.

Two seams, one in each direction:

* **outgoing** -- ``Interface.send_*`` (what ``client.py`` calls) fills ``_send_queue``;
  ``AgentV1._consumer`` drains it into a ``RuntimeInformation`` / ``RuntimeStatus`` pair.
* **incoming** -- ``AgentV1._receive_game_*`` fills ``_get_queue``; the same interface's
  ``consume_outgoing`` drains it back out.

Both are tested end to end here rather than by asserting the literal tag strings. Pinning
the strings would pass just as happily with both halves renamed in lockstep to something
the other side never sends; driving the real producer into the real decoder is what
actually catches a disagreement.

The queues are private (``_send_queue`` / ``_get_queue``); only these tests touch them
directly, and only to stand in for the half of the pair that is not under test.
"""

from __future__ import annotations

from typing import Any

import pytest
from harness import Interface, NetworkItem, RuntimeStatus


def drain(agent: Any, heartbeat: int = 0) -> tuple[Any, RuntimeStatus]:
    """Run one consumer tick over whatever the interface has queued."""
    result = agent._consumer(heartbeat)
    assert result is not None, "the consumer refused to run"
    return result


@pytest.fixture
def wired(sandbox: Any) -> tuple[Interface, Any]:
    """An interface and an agent sharing the interface's real queues.

    ``open_communication`` is what normally hands the agent these; going through it here
    would also start the worker thread and write the handshake, which would race every
    assertion below.
    """
    from harness import get_agent

    interface = Interface()
    agent = get_agent("0.0.0")()
    agent.htg_q = interface._send_queue
    agent.gth_q = interface._get_queue
    return interface, agent


def item(item_id: int = 1234, player: int = 2) -> NetworkItem:
    # NetworkItem(item, location, player, flags) -- only `item` is read back out.
    return NetworkItem(item_id, 55, player, 0)


# --- outgoing: Interface.send_* -> AgentV1._consumer -------------------------

def test_send_location_reaches_the_consumer(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface.send_location(4321)
    ri, _ = drain(agent)
    assert 4321 in ri.locations


def test_send_message_reaches_the_consumer(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface.send_message("Chelshia found Health Up")
    ri, _ = drain(agent)
    assert ri.messages == ["Chelshia found Health Up"]


def test_send_death_link_reaches_the_consumer(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface.send_death_link("squashed")
    ri, _ = drain(agent)
    assert ri.death_link == ["squashed"]


def test_send_item_reaches_the_consumer_with_its_order(wired: tuple[Interface, Any]) -> None:
    """``send_item`` packs ``(order, item)``; the serializer reads ``item[1].item, item[0]``.

    The tuple is heterogeneous and its halves are both plausible in either position, so a
    swap would not raise anywhere -- it would send an item id where an ordinal belongs.
    """
    interface, agent = wired
    interface.send_item(item(item_id=99), 7)
    ri, _ = drain(agent)
    assert len(ri.item_list) == 1
    order, network_item = ri.item_list[0]
    assert order == 7, "the ordinal and the item are swapped in the tuple"
    assert network_item.item == 99


def test_send_connection_status_true_means_connected(wired: tuple[Interface, Any]) -> None:
    """Spec: STATUS 0 is connected, 1 is disconnected -- the opposite of a bool.

    ``send_connection_status`` performs that inversion, so passing the bool straight
    through anywhere would report exactly the wrong state.
    """
    interface, agent = wired
    interface.send_connection_status(True)
    _, rs = drain(agent)
    assert rs.status == 0


def test_send_connection_status_false_means_disconnected(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface.send_connection_status(False)
    _, rs = drain(agent)
    assert rs.status == 1


def test_connection_status_persists_across_ticks(wired: tuple[Interface, Any]) -> None:
    """Status is latched, not per tick.

    The game reads STATUS from every ``ap.cs`` write, so a tick with nothing queued must
    keep reporting the last known value rather than reverting to the default.
    """
    interface, agent = wired
    interface.send_connection_status(True)
    drain(agent)
    _, rs = drain(agent, heartbeat=1)
    assert rs.status == 0, "status reverted on an idle tick"


def test_the_heartbeat_argument_reaches_the_status(wired: tuple[Interface, Any]) -> None:
    _, agent = wired
    _, rs = drain(agent, heartbeat=42)
    assert rs.heartbeat == 42


def test_one_tick_carries_every_kind_at_once(wired: tuple[Interface, Any]) -> None:
    """A realistic tick, to catch a tag that only collides when others are present."""
    interface, agent = wired
    interface.send_location(1)
    interface.send_location(2)
    interface.send_message("hello")
    interface.send_death_link("spikes")
    interface.send_item(item(item_id=5), 0)
    interface.send_connection_status(True)

    ri, rs = drain(agent)
    assert ri.locations == {1, 2}
    assert ri.messages == ["hello"]
    assert ri.death_link == ["spikes"]
    assert [i.item for _, i in ri.item_list] == [5]
    assert rs.status == 0


def test_the_consumer_empties_the_queue(wired: tuple[Interface, Any]) -> None:
    # A tick that leaves entries behind resends them next tick, duplicating every message.
    interface, agent = wired
    interface.send_location(1)
    drain(agent)
    assert interface._send_queue.qsize() == 0
    ri, _ = drain(agent)
    assert ri.locations == set(), "the same location was delivered twice"


def test_an_idle_tick_produces_empty_collections(wired: tuple[Interface, Any]) -> None:
    _, agent = wired
    ri, _ = drain(agent)
    assert ri.locations == set()
    assert ri.messages == []
    assert ri.death_link == []
    assert ri.item_list == []


def test_an_unknown_tag_is_ignored_rather_than_raising(wired: tuple[Interface, Any]) -> None:
    """The failure mode this module exists to document.

    No decoder branch matches, no ``else`` catches it, and the tick reports success. This
    is what a producer/decoder disagreement looks like from the outside -- which is why
    every test above drives the real producer instead of a literal tag.
    """
    interface, agent = wired
    interface._send_queue.put(("locaton", 1))  # one transposed letter
    ri, _ = drain(agent)
    assert ri.locations == set()


def test_the_consumer_declines_once_communication_is_closed(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface.send_location(1)
    agent.close_communication()
    assert agent._consumer(0) is None


def test_the_consumer_declines_on_a_shutdown_queue(wired: tuple[Interface, Any]) -> None:
    interface, agent = wired
    interface._send_queue.shutdown()
    assert agent._consumer(0) is None


def test_sending_after_shutdown_does_not_raise_into_the_client(wired: tuple[Interface, Any]) -> None:
    """``stop`` shuts the send queue down; the client may still be mid-callback.

    Every ``send_*`` swallows ``queue.ShutDown`` for this reason -- an item arriving one
    tick late must not raise out of an Archipelago network callback.
    """
    interface, _ = wired
    interface._send_queue.shutdown()
    interface.send_location(1)
    interface.send_message("late")
    interface.send_death_link("late")
    interface.send_item(item(), 0)
    interface.send_connection_status(True)


# --- incoming: AgentV1._receive_* -> Interface.consume_outgoing --------------

def test_a_location_from_the_game_reaches_consume_outgoing(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gi").write_text("LOC 77\n$", encoding="ascii")
    agent._receive_game_information()
    result = interface.consume_outgoing()
    assert result is not None
    assert 77 in result[0].locations


def test_a_death_link_from_the_game_reaches_consume_outgoing(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gi").write_text("DLINK spikes\n$", encoding="ascii")
    agent._receive_game_information()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].death_link == ["spikes"]


def test_an_ack_from_the_game_reaches_consume_outgoing(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gi").write_text("ACK 12\n$", encoding="ascii")
    agent._receive_game_information()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].ack == 12


def test_a_win_from_the_game_reaches_consume_outgoing(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gi").write_text("WIN\n$", encoding="ascii")
    agent._receive_game_information()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].is_win is True


def test_a_heartbeat_from_the_game_reaches_consume_outgoing(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gs").write_text("HBEAT 9\n$", encoding="ascii")
    agent._receive_game_status()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[1].heartbeat == 9


def test_the_ack_only_ever_advances(wired: tuple[Interface, Any], sandbox: Any) -> None:
    """A late or replayed document must not rewind the acknowledged item count.

    ``ap.gi`` can legitimately be read twice -- a stray ``.rd`` is recovered and merged --
    so an older ack arriving after a newer one is a normal occurrence, not a bug.
    """
    interface, agent = wired
    (sandbox / "ap.gi").write_text("ACK 12\n$", encoding="ascii")
    agent._receive_game_information()
    interface.consume_outgoing()

    (sandbox / "ap.gi").write_text("ACK 4\n$", encoding="ascii")
    agent._receive_game_information()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].ack == 12, "an older ack rewound the session"


def test_the_heartbeat_only_ever_advances(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gs").write_text("HBEAT 9\n$", encoding="ascii")
    agent._receive_game_status()
    interface.consume_outgoing()

    (sandbox / "ap.gs").write_text("HBEAT 2\n$", encoding="ascii")
    agent._receive_game_status()
    result = interface.consume_outgoing()
    assert result is not None
    assert result[1].heartbeat == 9, "an older heartbeat rewound the session"


def test_consume_outgoing_empties_the_queue(wired: tuple[Interface, Any], sandbox: Any) -> None:
    interface, agent = wired
    (sandbox / "ap.gi").write_text("LOC 77\n$", encoding="ascii")
    agent._receive_game_information()
    interface.consume_outgoing()
    assert interface._get_queue.qsize() == 0
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].locations == set(), "the same location was delivered twice"


def test_consume_outgoing_reports_none_on_a_shutdown_queue(wired: tuple[Interface, Any]) -> None:
    interface, _ = wired
    interface._get_queue.put(("location", 1))
    interface._get_queue.shutdown()
    assert interface.consume_outgoing() is None


def test_an_unknown_incoming_tag_is_ignored(wired: tuple[Interface, Any]) -> None:
    interface, _ = wired
    interface._get_queue.put(("hearbeat", 9))  # one transposed letter
    result = interface.consume_outgoing()
    assert result is not None
    assert result[1].heartbeat == -1


def test_a_full_round_trip_through_both_queues(wired: tuple[Interface, Any], sandbox: Any) -> None:
    """One document in, one tick out, checked at both ends of the interface."""
    interface, agent = wired
    interface.send_location(1)
    interface.send_connection_status(True)

    (sandbox / "ap.gi").write_text("LOC 77\nACK 3\nWIN\n$", encoding="ascii")
    agent._receive_game_information()

    outgoing_ri, outgoing_rs = drain(agent)
    assert outgoing_ri.locations == {1}
    assert outgoing_rs.status == 0

    incoming = interface.consume_outgoing()
    assert incoming is not None
    assert incoming[0].locations == {77}
    assert incoming[0].ack == 3
    assert incoming[0].is_win is True
