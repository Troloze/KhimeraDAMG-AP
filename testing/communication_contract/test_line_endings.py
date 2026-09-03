# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Contract: "Line endings should accept CRLF or LF on both the client and the game."

GameMaker Studio 1.4's file_text_writeln emits CRLF on Windows, so CRLF is the expected
shape of everything the game writes, not an edge case.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import code, contract, doc, payloads

GAME_ROWS = ["LOC 7654321", "DLINK squashed", "WIN", "ACK 9"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_document_parses(newline: str) -> None:
    events, _ = contract().parse_message(doc(*GAME_ROWS, newline=newline))
    assert len(events) == len(GAME_ROWS)


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_document_reports_no_errors(newline: str) -> None:
    assert code(contract().parse_message(doc(*GAME_ROWS, newline=newline))) == 0


def test_crlf_win_is_detected() -> None:
    # WIN is a single-token row, so it is the first casualty of a stray carriage return.
    events, _ = contract().parse_message(doc("LOC 1", "WIN", "ACK 2", newline="\r\n"))
    assert E.Win() in events


def test_crlf_terminator_is_recognised() -> None:
    # The terminator is also a single-token row.
    assert code(contract().parse_message(doc("ACK 9", newline="\r\n"))) == 0


def test_crlf_numeric_field_is_clean() -> None:
    events, _ = contract().parse_message(doc("ACK 9", newline="\r\n"))
    assert payloads(events) == payloads([E.Ack(9)])


def test_crlf_message_has_no_carriage_return() -> None:
    events, _ = contract().parse_message(doc("MSG hello world", "ACK 1", newline="\r\n"))
    messages = [e for e in events if isinstance(e, E.Message)]
    assert payloads(messages) == payloads([E.Message("hello world")])


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_read_game_info_sees_everything(newline: str) -> None:
    result = contract()._read_game_info(doc(*GAME_ROWS, newline=newline))
    assert result["is_win"] is True
    assert result["ack"] == 9
    assert result["locations"] == {7654321}
    assert result["death_link"] == ["squashed"]
