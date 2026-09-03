# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The reader runs on a 10 Hz loop against files another process is writing.

Contract: "Unknown identifiers should be skipped silently." A malformed *known*
identifier deserves the same treatment - the read tick must not raise.
"""

from __future__ import annotations

import pytest

from harness import contract, doc

# Documents that are terminated but contain bad rows.
BAD_ROWS = [
    pytest.param("ACK", id="truncated-ack"),
    pytest.param("LOC", id="truncated-loc"),
    pytest.param("LC 1 2", id="truncated-lc"),
    pytest.param("ITEM 5", id="truncated-item"),
    pytest.param("HBEAT", id="truncated-hbeat"),
    pytest.param("ACK abc", id="non-numeric-ack"),
    pytest.param("LOC 12.5", id="float-loc"),
    pytest.param("NOPE 1 2 3", id="unknown-identifier"),
    pytest.param("ACK 99999999999999999999999999", id="huge-number"),
    pytest.param("\x00\x01\x02", id="binary-noise"),
    pytest.param("MSG", id="message-without-text"),
    pytest.param("LOC  1", id="double-space"),
]

# Whole documents, including ones that are not terminated at all.
BAD_DOCUMENTS = [
    pytest.param("", id="empty-document"),
    pytest.param("\n", id="single-newline"),
    pytest.param("\n\n\n", id="blank-lines"),
    pytest.param("$", id="terminator-only"),
    pytest.param("ACK 1", id="unterminated"),
    pytest.param("ACK 1\nGARBAGE\nLOC 2", id="unterminated-with-garbage"),
    pytest.param(doc("ACK 1", "", "LOC 2"), id="blank-line-in-the-middle"),
    pytest.param(doc("$", "ACK 1"), id="terminator-in-the-middle"),
    *[pytest.param(doc(p.values[0]), id=p.id) for p in BAD_ROWS],
]


@pytest.mark.parametrize("blob", BAD_DOCUMENTS)
def test_parse_message_never_raises(blob: str) -> None:
    contract().parse_message(blob)


@pytest.mark.parametrize("blob", BAD_DOCUMENTS)
def test_read_game_info_never_raises(blob: str) -> None:
    contract()._read_game_info(blob)


@pytest.mark.parametrize("blob", BAD_DOCUMENTS)
def test_read_game_state_never_raises(blob: str) -> None:
    contract()._read_game_state(blob)


def test_read_game_state_on_empty_file() -> None:
    # ap.gs is read without the .rd rename, so catching it mid-replace is expected.
    assert contract()._read_game_state("")["heartbeat"] == -1


def test_read_game_state_reads_a_well_formed_heartbeat() -> None:
    assert contract()._read_game_state(doc("HBEAT 12"))["heartbeat"] == 12


def test_read_game_state_always_reports_an_exit_code() -> None:
    # The three return paths must agree on their shape, or callers KeyError on the
    # happy path only.
    assert "exit_code" in contract()._read_game_state(doc("HBEAT 12"))


def test_valid_rows_survive_a_bad_neighbour() -> None:
    result = contract()._read_game_info(doc("LOC 1", "GARBAGE ROW", "LOC 2", "ACK 4"))
    assert result["locations"] == {1, 2}
    assert result["ack"] == 4


def test_blank_line_is_not_reported_as_an_unknown_identifier(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="Client"):
        contract().parse_message(doc("ACK 1", "", "LOC 2"))
    offenders = [r for r in caplog.records if "unknown flag" in r.getMessage().lower()]
    assert not offenders, [r.getMessage() for r in offenders]


def test_multiple_deathlinks_in_one_tick_are_not_lost() -> None:
    result = contract()._read_game_info(doc("DLINK first", "DLINK second", "ACK 1"))
    assert result["death_link"] == ["first", "second"]


def test_message_less_deathlink_is_accepted() -> None:
    # The implementation deliberately allows a bare DLINK.
    result = contract()._read_game_info(doc("DLINK", "ACK 1"))
    assert result["death_link"] == [""]
