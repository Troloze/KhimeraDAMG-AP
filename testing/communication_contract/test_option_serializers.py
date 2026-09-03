# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The OPTION serializers, against the "Type treatment specification" section of the spec.

  S - single value, integer or string
  L - list, preceded by a count; every value the same type
  D - dictionary, preceded by a field count; keys sorted, keys always strings
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import EventSerializer, OptionSerializer

SER = EventSerializer
OPT = OptionSerializer


# --- Choice (S) -------------------------------------------------------------

def test_choice_emits_single_tagged_row() -> None:
    assert OPT.choice(("victory_condition", 2)) == "OPTION victory_condition S 2"


def test_choice_rejects_negative_values() -> None:
    # Spec: "Value must be a non negative integer."
    with pytest.raises(ValueError):
        OPT.choice(("victory_condition", -1))


def test_choice_accepts_zero() -> None:
    assert OPT.choice(("victory_condition", 0)) == "OPTION victory_condition S 0"


# --- Toggle (S) -------------------------------------------------------------

@pytest.mark.parametrize(("value", "expected"), [(0, "0"), (1, "1"), (False, "0"), (True, "1")])
def test_toggle_emits_zero_or_one(value: object, expected: str) -> None:
    assert OPT.toggle(("death_link", value)) == f"OPTION death_link S {expected}"


def test_toggle_rejects_values_outside_zero_and_one() -> None:
    # Spec: "Value must be an integer, either 0 or 1."
    with pytest.raises(ValueError):
        OPT.toggle(("death_link", 2))


# --- Range (S) --------------------------------------------------------------

def test_range_emits_single_tagged_row() -> None:
    assert OPT.range(("cakeboy_progression_locations", 25)) == "OPTION cakeboy_progression_locations S 25"


def test_range_allows_negative_values() -> None:
    # Spec only says "Value must be an integer" for Range, unlike Choice.
    assert OPT.range(("some_range", -3)) == "OPTION some_range S -3"


# --- OptionList (L) ---------------------------------------------------------

def test_list_emits_count_then_values() -> None:
    assert OPT.op_list(("collectablesanity", ["coin", "gems"])) == "OPTION collectablesanity L 2 coin gems"


def test_list_of_integers() -> None:
    assert OPT.op_list(("some_list", [3, 1, 2])) == "OPTION some_list L 3 3 1 2"


def test_empty_list_emits_zero_count() -> None:
    assert OPT.op_list(("collectablesanity", [])) == "OPTION collectablesanity L 0"


def test_list_rejects_mixed_types() -> None:
    # Spec: "All values on the list have to be of the same type."
    with pytest.raises(TypeError):
        OPT.op_list(("some_list", ["coin", 2]))


def test_list_rejects_whitespace_in_values() -> None:
    with pytest.raises(ValueError):
        OPT.op_list(("some_list", ["two words"]))


def test_single_element_list_is_still_validated() -> None:
    # Every element is type-checked, not just compared against values[0].
    with pytest.raises(TypeError):
        OPT.op_list(("some_list", [None]))


def test_list_rejects_line_breaks_in_values() -> None:
    # Spec: strings "Must not use line breaks" - a newline would split the row in two.
    with pytest.raises(ValueError):
        OPT.op_list(("some_list", ["two\nlines"]))


def test_list_rejects_tabs_in_values() -> None:
    # Spec: "String params will not contain whitespaces".
    with pytest.raises(ValueError):
        OPT.op_list(("some_list", ["two\ttabs"]))


# --- OptionSet (L) ----------------------------------------------------------

def test_set_emits_sorted_values() -> None:
    # Spec: "string values must be sorted".
    assert OPT.op_set(("collectablesanity", {"gems", "coin", "food"})) == "OPTION collectablesanity L 3 coin food gems"


def test_set_output_is_stable_regardless_of_input_order() -> None:
    a = OPT.op_set(("collectablesanity", ["gems", "coin", "food"]))
    b = OPT.op_set(("collectablesanity", ["food", "gems", "coin"]))
    assert a == b


def test_empty_set_emits_zero_count() -> None:
    assert OPT.op_set(("collectablesanity", set())) == "OPTION collectablesanity L 0"


def test_set_rejects_whitespace_in_values() -> None:
    with pytest.raises(ValueError):
        OPT.op_set(("collectablesanity", {"two words"}))


# --- OptionCount (D) --------------------------------------------------------

def test_count_emits_field_count_then_sorted_pairs() -> None:
    value = {"stage_main": 1, "fairies": 5, "books": 2}
    assert OPT.op_count(("access_cost", value)) == "OPTION access_cost D 3 books 2 fairies 5 stage_main 1"


def test_count_output_is_stable_regardless_of_input_order() -> None:
    a = OPT.op_count(("access_cost", {"fairies": 5, "books": 2}))
    b = OPT.op_count(("access_cost", {"books": 2, "fairies": 5}))
    assert a == b


def test_empty_count_emits_zero_field_count() -> None:
    assert OPT.op_count(("access_cost", {})) == "OPTION access_cost D 0"


def test_count_rejects_non_integer_values() -> None:
    # Spec: "A dictionary where all values are integers."
    with pytest.raises(ValueError):
        OPT.op_count(("access_cost", {"fairies": "many"}))


def test_count_normalises_booleans_to_integers() -> None:
    assert OPT.op_count(("access_cost", {"fairies": True})) == "OPTION access_cost D 1 fairies 1"


def test_count_rejects_whitespace_in_keys() -> None:
    with pytest.raises(ValueError):
        OPT.op_count(("access_cost", {"two words": 1}))


# --- dispatch tables --------------------------------------------------------

def test_every_registered_option_serializer_exists() -> None:
    missing = [name for name in OPT.serializers.values() if not hasattr(OPT, name)]
    assert not missing, f"option_serializers points at undefined methods: {missing}"


def test_every_option_type_has_a_serializer() -> None:
    unregistered = sorted({t for t in OPT.types.values() if t not in OPT.serializers})
    assert not unregistered, f"option_types uses types with no serializer: {unregistered}"


def test_option_list_type_is_registered() -> None:
    # op_list is implemented and the spec lists OptionList (L) as a supported type.
    assert "option_list" in OPT.serializers


def test_every_option_serializer_method_is_reachable() -> None:
    implemented = {n for n in vars(OPT) if not n.startswith("_")} - {"serialize", "serializers", "types"}
    registered = set(OPT.serializers.values())
    assert not implemented - registered, f"unreachable serializers: {sorted(implemented - registered)}"


@pytest.mark.parametrize("option_name", sorted(OPT.types))
def test_serialize_ap_option_round_dispatches_every_declared_option(option_name: str) -> None:
    row = SER.serialize_ap_option(E.ApOption(option_name, 1))
    assert row.startswith(f"OPTION {option_name} ")


def test_unknown_option_is_dropped_not_raised() -> None:
    assert SER.serialize_ap_option(E.ApOption("not_an_option", 1)) == ""
