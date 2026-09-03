# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The dollar-sign terminator added to contract v1.

Spec, File Structure: "The last line on every file will be a sole dollar sign."

The reader's exit code is a bit flag:
  bit 0 (value 1) - at least one line was malformed or unrecognised
  bit 1 (value 2) - the file was incomplete (no terminator)
"""

from __future__ import annotations

import pytest

from harness import TERMINATOR
from harness import CommunicationEvent as E
from harness import code, contract, doc, payloads, raw_rows

MALFORMED_BIT = 0b01
INCOMPLETE_BIT = 0b10


# --- writing ----------------------------------------------------------------

def test_every_written_document_ends_with_the_terminator() -> None:
    assert raw_rows(contract().parse_events([E.Heartbeat(1)]))[-1] == TERMINATOR


def test_terminator_is_present_even_for_an_empty_event_list() -> None:
    assert raw_rows(contract().parse_events([])) == [TERMINATOR]


@pytest.mark.parametrize("content_type", ["cctx", "hi", "cs", "li"])
def test_every_file_writer_terminates_its_document(content_type: str) -> None:
    from test_file_writers import cctx_params, host_info_params

    params = {
        "cctx": cctx_params(),
        "hi": host_info_params(),
        "cs": {"status": 0, "heartbeat": 1},
        "li": {"enabled": 0, "loc_info": None},
    }[content_type]
    assert raw_rows(contract().write_content(content_type, params))[-1] == TERMINATOR


# --- reading ----------------------------------------------------------------

def test_terminated_document_reports_no_error() -> None:
    """A complete, well-formed file must come back with exit code 0."""
    assert code(contract().parse_message(doc("ACK 9"))) == 0


def test_terminator_is_not_reported_as_an_unknown_identifier(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="Client"):
        contract().parse_message(doc("ACK 9"))
    offenders = [r for r in caplog.records if "unknown flag" in r.getMessage().lower()]
    assert not offenders, [r.getMessage() for r in offenders]


def test_terminator_does_not_become_an_event() -> None:
    events, _ = contract().parse_message(doc("ACK 9"))
    assert payloads(events) == payloads([E.Ack(9)])


def test_missing_terminator_sets_the_incomplete_bit() -> None:
    assert code(contract().parse_message(doc("ACK 9", terminated=False))) & INCOMPLETE_BIT


def test_terminated_document_does_not_set_the_incomplete_bit() -> None:
    assert not code(contract().parse_message(doc("ACK 9"))) & INCOMPLETE_BIT


def test_malformed_row_sets_the_malformed_bit() -> None:
    assert code(contract().parse_message(doc("ACK", "LOC 1"))) & MALFORMED_BIT


def test_clean_document_does_not_set_the_malformed_bit() -> None:
    assert not code(contract().parse_message(doc("LOC 1", "ACK 2"))) & MALFORMED_BIT


def test_both_bits_can_be_set_together() -> None:
    result_code = code(contract().parse_message(doc("ACK", terminated=False)))
    assert result_code & MALFORMED_BIT
    assert result_code & INCOMPLETE_BIT


def test_empty_document_is_reported_as_incomplete_not_crashed() -> None:
    """An ap.gs read caught mid-replace yields an empty string."""
    assert code(contract().parse_message("")) & INCOMPLETE_BIT
