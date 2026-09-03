# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The DATA serializers, against the "Type treatment specification" section of the spec.

DATA rows carry generation information the game needs (map/entrance randomiser data).
They use the same S / L / D type tags as OPTION rows, but the identifier is DATA.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import ContractV1, DataSerializer, EventSerializer

SER = EventSerializer
DAT = DataSerializer


# --- Single values (S) ------------------------------------------------------

def test_int_value_emits_data_row() -> None:
    assert DAT.int_value(("stage_count", 6)) == "DATA stage_count S 6"


def test_int_value_allows_negatives() -> None:
    assert DAT.int_value(("offset", -2)) == "DATA offset S -2"


@pytest.mark.parametrize(("value", "expected"), [(0, "0"), (1, "1"), (False, "0"), (True, "1")])
def test_bool_value_emits_zero_or_one(value: object, expected: str) -> None:
    assert DAT.bool_value(("mountains_shuffled", value)) == f"DATA mountains_shuffled S {expected}"


def test_str_value_emits_data_row() -> None:
    assert DAT.str_value(("start_stage", "mt_afrokupa")) == "DATA start_stage S mt_afrokupa"


def test_str_value_rejects_whitespace() -> None:
    with pytest.raises(ValueError):
        DAT.str_value(("start_stage", "mt afrokupa"))


def test_str_value_rejects_line_breaks() -> None:
    # Spec: "Must not use line breaks." A newline here splits the row in two.
    with pytest.raises(ValueError):
        DAT.str_value(("start_stage", "mt\nafrokupa"))


def test_str_value_rejects_tabs() -> None:
    with pytest.raises(ValueError):
        DAT.str_value(("start_stage", "mt\tafrokupa"))


def test_str_value_leaves_ascii_enforcement_to_serialize_event() -> None:
    # The ASCII policy is applied once, at the serialize_event level, rather than being
    # duplicated in every serializer. See test_ascii_policy.py.
    assert DAT.str_value(("start_stage", "café")) == "DATA start_stage S café"


# --- Lists (L) --------------------------------------------------------------

def test_list_value_emits_count_then_values() -> None:
    assert DAT.list_value(("stage_order", ["a", "b", "c"])) == "DATA stage_order L 3 a b c"


def test_list_value_of_integers() -> None:
    assert DAT.list_value(("stage_order", [3, 1, 2])) == "DATA stage_order L 3 3 1 2"


def test_empty_list_value_emits_zero_count() -> None:
    assert DAT.list_value(("stage_order", [])) == "DATA stage_order L 0"


def test_list_value_rejects_mixed_types() -> None:
    with pytest.raises(TypeError):
        DAT.list_value(("stage_order", ["a", 2]))


def test_list_value_rejects_whitespace_in_values() -> None:
    with pytest.raises(ValueError):
        DAT.list_value(("stage_order", ["two words"]))


def test_list_value_preserves_order() -> None:
    # Unlike OptionSet, a list's order is meaningful and must not be sorted.
    assert DAT.list_value(("stage_order", ["c", "a", "b"])) == "DATA stage_order L 3 c a b"


# --- Dictionaries (D) -------------------------------------------------------

def test_dict_value_emits_a_data_row_not_an_option_row() -> None:
    row = DAT.dict_value(("entrances", {"b": 2, "a": 1}))
    assert row.startswith("DATA "), f"DataSerializer emitted the wrong identifier: {row!r}"


def test_dict_value_emits_field_count_then_sorted_pairs() -> None:
    assert DAT.dict_value(("entrances", {"b": 2, "a": 1})) == "DATA entrances D 2 a 1 b 2"


def test_dict_value_accepts_string_values() -> None:
    # Unlike OptionCount, Data dictionaries may mix integer and string values.
    assert DAT.dict_value(("entrances", {"a": "home"})) == "DATA entrances D 1 a home"


def test_dict_value_rejects_whitespace_in_keys() -> None:
    with pytest.raises(ValueError):
        DAT.dict_value(("entrances", {"two words": 1}))


def test_dict_value_rejects_whitespace_in_string_values() -> None:
    with pytest.raises(ValueError):
        DAT.dict_value(("entrances", {"a": "two words"}))


def test_dict_value_rejects_unsupported_value_types() -> None:
    with pytest.raises(ValueError):
        DAT.dict_value(("entrances", {"a": [1, 2]}))


def test_empty_dict_value_emits_zero_field_count() -> None:
    assert DAT.dict_value(("entrances", {})) == "DATA entrances D 0"


# --- dispatch tables --------------------------------------------------------

def test_every_registered_data_serializer_exists() -> None:
    missing = [name for name in DAT.serializers.values() if not hasattr(DAT, name)]
    assert not missing, f"data_serializers points at undefined methods: {missing}"


def test_every_data_type_has_a_serializer() -> None:
    unregistered = sorted({t for t in DAT.types.values() if t not in DAT.serializers})
    assert not unregistered, f"data_types uses types with no serializer: {unregistered}"


def test_every_data_serializer_method_is_reachable() -> None:
    implemented = {n for n in vars(DAT) if not n.startswith("_")} - {"serialize", "serializers", "types"}
    registered = set(DAT.serializers.values())
    assert not implemented - registered, f"unreachable serializers: {sorted(implemented - registered)}"


def test_serialize_slot_data_dispatches_by_declared_type() -> None:
    """A contract version that declares a DATA entry must be able to serialize it."""
    DataSerializer.types["stage_count"] = "int"
    try:
        assert DataSerializer.serialize("stage_count", 6) == "DATA stage_count S 6"
    finally:
        del DataSerializer.types["stage_count"]


def test_unknown_data_is_dropped_not_raised() -> None:
    assert SER.serialize_slot_data(E.SlotData("not_a_data_entry", 1)) == ""
