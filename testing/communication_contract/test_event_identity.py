# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Event equality, and what the three control flags do to it.

``Event`` carries ``invalid``, ``validate_enabled`` and ``sanitize_enabled``, declared
``compare=False, repr=False`` so they stay constructor knobs rather than becoming part of
the value.

That distinction is load-bearing: the deserializers construct every event with
``sanitize_enabled=False`` (correctly -- a value read off the wire is already escaped and
must not be escaped again). Were the flags comparable, nothing read from the game would
ever ``==`` the same event built in client code, or land in the same set or dict bucket,
and every such comparison would silently miss.

These tests guard that they stay non-comparing, and that they still behave as flags.
"""

from __future__ import annotations

import dataclasses

import pytest

from harness import CONTROL_FLAGS
from harness import CommunicationEvent as E
from harness import contract, payload, payloads, text


# --- the flags are fields ---------------------------------------------------

@pytest.mark.parametrize("flag", CONTROL_FLAGS)
def test_each_control_flag_is_a_dataclass_field(flag: str) -> None:
    assert flag in {f.name for f in dataclasses.fields(E.Heartbeat)}


@pytest.mark.parametrize("flag", CONTROL_FLAGS)
def test_control_flags_are_keyword_only(flag: str) -> None:
    """Positional construction must stay unchanged as flags are added.

    ``E.Heartbeat(7)`` has to keep meaning ``value=7``; if a flag were positional it
    would silently capture the first argument instead.
    """
    field = next(f for f in dataclasses.fields(E.Heartbeat) if f.name == flag)
    assert field.kw_only


def test_positional_construction_still_binds_the_value() -> None:
    assert E.Heartbeat(7).value == 7
    assert E.LocationClassification(1, 2, 3).player_id == 3


def test_invalid_disables_both_other_flags() -> None:
    # __post_init__ forces this, so an event marked invalid can hold anything.
    event = E.Heartbeat(-1, invalid=True)
    assert event.validate_enabled is False
    assert event.sanitize_enabled is False
    assert event.value == -1


def test_an_invalid_event_skips_validation_that_would_otherwise_raise() -> None:
    # The escape hatch the deserializers need for a row they want to keep but not trust.
    assert E.ConnectionStatus(9, invalid=True).value == 9


# --- what that does to equality ---------------------------------------------

@pytest.mark.parametrize("flag", CONTROL_FLAGS)
def test_control_flags_do_not_take_part_in_equality(flag: str) -> None:
    assert E.Heartbeat(7) == E.Heartbeat(7, **{flag: True})
    assert E.Heartbeat(7) == E.Heartbeat(7, **{flag: False})


def test_a_deserialized_event_equals_the_constructed_one() -> None:
    """The round trip the client actually performs.

    Every deserializer passes ``sanitize_enabled=False``; with the flags excluded from
    ``__eq__`` an event off the wire still equals one written in client code, so an
    ``event == ...`` check means what it looks like it means.
    """
    events, _ = contract().parse_message("HBEAT 7\n$")
    assert events[0] == E.Heartbeat(7)


def test_the_flags_do_not_split_hash_buckets() -> None:
    """Frozen dataclasses hash on the same fields they compare on."""
    assert hash(E.Heartbeat(7)) == hash(E.Heartbeat(7, sanitize_enabled=False))
    assert E.Heartbeat(7) in {E.Heartbeat(7, sanitize_enabled=False)}


def test_the_flags_are_hidden_from_repr() -> None:
    # A log line showing three constant flags on every event is noise.
    assert repr(E.Heartbeat(7)).count("=") == 1


def test_payload_comparison_ignores_the_flags() -> None:
    # The helper the round-trip suite uses. Redundant with plain == while the flags stay
    # non-comparing, which is the point: it keeps those tests pinned to the wire format
    # even if the flags are ever made part of the value again.
    assert payload(E.Heartbeat(7)) == payload(E.Heartbeat(7, sanitize_enabled=False))


def test_payload_still_distinguishes_different_values() -> None:
    assert payload(E.Heartbeat(7)) != payload(E.Heartbeat(8))


def test_payload_still_distinguishes_different_event_types() -> None:
    # LACK 7 and ACK 7 serialize to different rows; they must not compare equal.
    assert payload(E.LastAck(7)) != payload(E.Ack(7))


def test_flags_do_not_reach_the_wire() -> None:
    """Whatever the flags do to equality, they must not appear in a serialized row."""
    written, _ = contract().parse_events([E.Heartbeat(7, sanitize_enabled=False)])
    rows = [r for r in text((written, 0)).splitlines() if r]
    assert rows[0] == "HBEAT 7"


def test_a_full_document_round_trips_by_payload() -> None:
    events = [E.Ack(3), E.LocationChecked(12), E.Heartbeat(1)]
    c = contract()
    read, _ = c.parse_message(text(c.parse_events(events)))
    assert payloads(read) == payloads(events)
