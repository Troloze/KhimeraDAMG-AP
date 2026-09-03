# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The per-file writers and the write_content / read_content facade."""

from __future__ import annotations

import pytest

from harness import NetworkItem, code, contract, doc, rows

# Three received items; the second and third share an item id, which is how Archipelago
# represents a duplicate (items_received is a flat list, there is no count field).
ITEMS = [
    (1, NetworkItem(item=100, location=11, player=1, flags=1)),
    (2, NetworkItem(item=200, location=22, player=1, flags=0)),
    (3, NetworkItem(item=200, location=33, player=2, flags=0)),
]


def cctx_params(**overrides: object) -> dict[str, object]:
    params: dict[str, object] = {
        "ap_version": "0.6.7",
        "host_world_version": "0.0.2",
        "client_world_version": "0.0.2",
        "slot_name": "Chelshia",
        "options": {"death_link": 1, "victory_condition": 0},
        "slot_data": {},
        "last_ack": 0,
        "item_list": list(ITEMS),
        "locations": {7654321},
        "has_goaled": False,
    }
    params.update(overrides)
    return params


def host_info_params(**overrides: object) -> dict[str, object]:
    params: dict[str, object] = {
        "messages": ["first", "second"],
        "item_list": list(ITEMS[:2]),
        "death_link": ["squashed"],
        "locations": {7654321},
    }
    params.update(overrides)
    return params


# --- ap.cctx ----------------------------------------------------------------

def test_cctx_rows_are_separated() -> None:
    """Every identifier must land on its own row; the file is a list of rows."""
    written = contract()._write_context(cctx_params())
    assert len(rows(written)) > 1, f"whole document collapsed onto one row: {written!r}"


def test_cctx_reports_success() -> None:
    assert code(contract()._write_context(cctx_params())) == 0


def test_cctx_item_rows_are_item_id_then_index() -> None:
    """Spec: ITEM <item_id: int> <index: int>, index 0-excluded."""
    item_rows = [r for r in rows(contract()._write_context(cctx_params())) if r.startswith("ITEM ")]
    assert item_rows == ["ITEM 100 1", "ITEM 200 2", "ITEM 200 3"]


def test_cctx_contains_the_mandatory_headers() -> None:
    written = rows(contract()._write_context(cctx_params()))
    for expected in ("APV 0.6.7", "APW 0.0.2", "CAPW 0.0.2", "SLOT Chelshia", "LACK 0"):
        assert expected in written


def test_cctx_contains_checked_locations_and_options() -> None:
    written = rows(contract()._write_context(cctx_params()))
    assert "LOC 7654321" in written
    assert "OPTION death_link S 1" in written
    assert "OPTION victory_condition S 0" in written


def test_cctx_omits_win_when_not_goaled() -> None:
    assert "WIN" not in rows(contract()._write_context(cctx_params(has_goaled=False)))


def test_cctx_reports_an_already_reached_goal() -> None:
    # Spec ap.cctx identifier 10: WIN informs the game it has already reached its goal.
    assert "WIN" in rows(contract()._write_context(cctx_params(has_goaled=True)))


def test_cctx_missing_key_is_reported() -> None:
    params = cctx_params()
    del params["slot_name"]
    with pytest.raises((KeyError, ValueError)):
        contract()._write_context(params)


# --- ap.in ------------------------------------------------------------------

def test_host_info_rows_are_separated() -> None:
    written = contract()._write_host_info(host_info_params())
    assert len(rows(written)) > 1, f"whole document collapsed onto one row: {written!r}"


def test_host_info_item_rows_are_item_id_then_index() -> None:
    item_rows = [r for r in rows(contract()._write_host_info(host_info_params())) if r.startswith("ITEM ")]
    assert item_rows == ["ITEM 100 1", "ITEM 200 2"]


def test_host_info_carries_messages_deathlinks_and_locations() -> None:
    written = rows(contract()._write_host_info(host_info_params()))
    for expected in ("MSG first", "MSG second", "DLINK squashed", "LOC 7654321"):
        assert expected in written


def test_host_info_passes_messages_through_uncapped() -> None:
    """Capping now lives in the agent, which prunes its buffer before calling the writer.

    Documented here rather than asserted the other way round so that if enforcement moves
    back into the contract, this test says so instead of silently double-capping. The
    agent-side guarantee is covered by test_file_transport's buffer-pruning test.
    """
    c = contract()
    cap = c.max_messages_per_tick
    msgs = [f"m{i}" for i in range(cap + 10)]
    msg_rows = [r for r in rows(c._write_host_info(host_info_params(messages=msgs))) if r.startswith("MSG ")]
    assert len(msg_rows) == cap + 10
    assert msg_rows[-1] == f"MSG m{cap + 9}"


@pytest.mark.parametrize("content_type", ["cctx", "hi", "cs", "li"])
def test_write_content_dispatches(content_type: str) -> None:
    params = {
        "cctx": cctx_params(),
        "hi": host_info_params(),
        "cs": {"status": 0, "heartbeat": 1},
        "li": {"enabled": 0, "loc_info": None},
    }[content_type]
    payload, exit_code = contract().write_content(content_type, params)
    assert isinstance(payload, str)
    assert isinstance(exit_code, int)


def test_write_content_rejects_unknown_type() -> None:
    with pytest.raises(ValueError):
        contract().write_content("nope", {})


def test_read_content_gi_returns_the_parsed_payload() -> None:
    result = contract().read_content("gi", doc("LOC 1", "WIN", "ACK 3"))
    assert isinstance(result, dict), f"read_content returned {result!r}"
    assert result["locations"] == {1}
    assert result["is_win"] is True
    assert result["ack"] == 3


def test_read_content_gs_returns_the_heartbeat() -> None:
    result = contract().read_content("gs", doc("HBEAT 12"))
    assert isinstance(result, dict), f"read_content returned {result!r}"
    assert result["heartbeat"] == 12


def test_read_content_rejects_unknown_type() -> None:
    with pytest.raises(ValueError):
        contract().read_content("nope", "")


def test_deathlink_payload_is_the_message_not_the_whole_document() -> None:
    result = contract()._read_game_info(doc("LOC 1", "DLINK squashed", "ACK 2"))
    assert result["death_link"] == ["squashed"]


def test_read_game_info_reports_a_clean_document() -> None:
    assert contract()._read_game_info(doc("LOC 1", "ACK 2"))["exit_code"] == 0
