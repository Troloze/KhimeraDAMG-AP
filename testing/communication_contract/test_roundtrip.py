# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""serialize -> deserialize must be the identity for every event the contract defines.

This is the cheapest possible guard against the two tables (event_to_parser and
flag_to_parser) drifting apart.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import code, contract, payloads, text

ROUND_TRIPPABLE = [
    E.ApVersion("0.6.7"),
    E.HostWorldVersion("0.0.2"),
    E.ClientWorldVersion("9.9.9"),
    E.SlotName("Chelshia"),
    E.LastAck(7),
    E.ItemReceived(1234567, 3),
    E.LocationChecked(7654321),
    E.LocationClassificationPreview(1),
    E.LocationClassification(7654321, 3, 2),
    E.Message("Chelshia found Health Up"),
    E.DeathLink("squashed"),
    E.Ack(9),
    E.Win(),
    E.ConnectionStatus(0),
    E.Heartbeat(42),
]


def round_trip(events: list[object]) -> list[object]:
    c = contract()
    written = c.parse_events(events)
    read, _ = c.parse_message(text(written))
    return read


@pytest.mark.parametrize("event", ROUND_TRIPPABLE, ids=lambda e: type(e).__name__)
def test_single_event_round_trips(event: object) -> None:
    assert payloads(round_trip([event])) == payloads([event])


def test_full_document_round_trips() -> None:
    assert payloads(round_trip(ROUND_TRIPPABLE)) == payloads(ROUND_TRIPPABLE)


def test_round_trip_reports_no_errors() -> None:
    c = contract()
    written = c.parse_events(ROUND_TRIPPABLE)
    assert code(written) == 0, "serializer reported a failure"
    assert code(c.parse_message(text(written))) == 0, "deserializer reported a failure"


def test_host_and_client_world_versions_do_not_swap() -> None:
    # APW is the host's apworld version, CAPW is the client's. Distinct values so a
    # swapped mapping cannot pass by coincidence.
    events = [E.HostWorldVersion("1.1.1"), E.ClientWorldVersion("2.2.2")]
    assert payloads(round_trip(events)) == payloads(events)


def test_location_classification_fields_do_not_swap() -> None:
    # LC <location_id> <class> <player> - three distinct values so a repeated index
    # or a reordering cannot pass by coincidence.
    event = E.LocationClassification(7654321, 4, 9)
    assert payloads(round_trip([event])) == payloads([event])


def test_reader_accepts_a_signed_number() -> None:
    # Spec: "signs must be connected to the number without a whitespace between them."
    # No event field is signed today, but the wire format still permits one.
    events, _ = contract().parse_message("\n".join(["HBEAT +12", "$"]))
    assert payloads(events) == payloads([E.Heartbeat(12)])
