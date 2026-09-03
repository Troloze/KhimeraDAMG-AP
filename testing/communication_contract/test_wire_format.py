# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Every identifier's on-the-wire form, asserted against docs/Communication Contract v1.md.

These tests encode the specification, not the current implementation. A failure here means
the bytes the client would put on disk do not match what the contract promises the game.
"""

from __future__ import annotations

import pytest

from harness import TERMINATOR
from harness import CommunicationEvent as E
from harness import code, contract, raw_rows, rows


@pytest.mark.parametrize(("event", "expected"), [
    # --- ap.cctx -------------------------------------------------------------
    (E.ApVersion("0.6.7"), "APV 0.6.7"),
    (E.HostWorldVersion("0.0.2"), "APW 0.0.2"),
    (E.ClientWorldVersion("0.0.2"), "CAPW 0.0.2"),
    (E.SlotName("Chelshia"), "SLOT Chelshia"),
    (E.LastAck(7), "LACK 7"),
    # spec: ITEM <item_id: int> <index: int>
    (E.ItemReceived(1234567, 3), "ITEM 1234567 3"),
    (E.LocationChecked(7654321), "LOC 7654321"),
    # --- ap.li ---------------------------------------------------------------
    (E.LocationClassificationPreview(1), "LCPV 1"),
    (E.LocationClassification(7654321, 3, 2), "LC 7654321 3 2"),
    # --- ap.cs ---------------------------------------------------------------
    (E.ConnectionStatus(0), "STATUS 0"),
    (E.Heartbeat(42), "HBEAT 42"),
    # --- ap.in ---------------------------------------------------------------
    (E.Message("Chelshia found Health Up"), "MSG Chelshia found Health Up"),
    (E.DeathLink("squashed"), "DLINK squashed"),
    # --- ap.out --------------------------------------------------------------
    (E.Ack(9), "ACK 9"),
    (E.Win(), "WIN"),
])
def test_event_serializes_to_spec_row(event: object, expected: str) -> None:
    assert rows(contract().parse_events([event])) == [expected]


def test_known_option_serializes() -> None:
    assert rows(contract().parse_events([E.ApOption("death_link", 1)])) == ["OPTION death_link S 1"]


def test_unknown_option_is_dropped_not_crashed() -> None:
    # An option the contract version does not know about must be skipped, not raised on.
    assert rows(contract().parse_events([E.ApOption("some_future_option", 1)])) == []


def test_unknown_option_sets_the_failure_exit_code() -> None:
    assert code(contract().parse_events([E.ApOption("some_future_option", 1)])) == 1


def test_fully_serializable_document_reports_success() -> None:
    assert code(contract().parse_events([E.Heartbeat(1), E.ConnectionStatus(0)])) == 0


def test_multiple_events_are_newline_joined() -> None:
    assert rows(contract().parse_events([E.Heartbeat(1), E.ConnectionStatus(0)])) == ["HBEAT 1", "STATUS 0"]


def test_win_row_has_no_trailing_space() -> None:
    # WIN takes no parameters; a trailing space would make row[0] parsing ambiguous.
    assert rows(contract().parse_events([E.Win()])) == ["WIN"]
