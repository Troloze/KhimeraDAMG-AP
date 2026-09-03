# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""ASCII enforcement.

Spec: "All files are encoded in ASCII".

The policy changed with ``normalize_and_sanitize``: a non-ASCII string value is no longer
*rejected* at construction, it is *transliterated* -- ``sanitize_string`` runs the
normaliser before ``validate_string`` checks the result, so by the time validation runs
the value is already ASCII. Rejection is now reserved for what cannot be repaired:
whitespace in a field the wire format splits on, and values of an unsupported type.

This holds for option list entries too: ``sanitize_option_data`` normalises each string
entry, so the two paths agree. A ``dict`` value is the one shape still rejected outright.

The character-level behaviour of the normaliser itself is covered by
``testing/misc/encoding``; this module only asserts which policy each field follows.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import EventSerializer, EventTypeError, EventValueError, normalised

SER = EventSerializer

NON_ASCII = ["Renée", "Ωmega", "日本", "café", "naïve"]


# --- normalised at construction ---------------------------------------------

@pytest.mark.parametrize("value", NON_ASCII)
def test_slot_name_is_normalised_not_rejected(value: str) -> None:
    """A player's YAML name is not something the client gets to refuse.

    Rejecting here raises out of the handshake write and fails the whole connection; the
    normaliser exists so an accented slot name degrades to a readable ASCII one instead.
    """
    assert E.SlotName(value).name.isascii()


@pytest.mark.parametrize("value", NON_ASCII)
def test_message_is_normalised_not_rejected(value: str) -> None:
    assert E.Message(value).message.isascii()


@pytest.mark.parametrize("value", NON_ASCII)
def test_deathlink_is_normalised_not_rejected(value: str) -> None:
    assert E.DeathLink(value).message.isascii()


def test_a_known_accent_transliterates_rather_than_degrading(value: str = "Renée") -> None:
    # "Rene_" or "Rene_e" would be ASCII but unrecognisable; the point of NFKD is the
    # base letter survives.
    assert E.SlotName(value).name == "Renee"


def test_option_name_is_normalised(value: str = "café") -> None:
    assert E.ApOption(value, 1).name.isascii()


def test_option_string_value_is_normalised() -> None:
    assert E.ApOption("some_option", "café").value.isascii()


def test_option_list_entries_are_normalised_too() -> None:
    """Both sanitisers now run the normaliser, so the two paths agree.

    They did not always: ``sanitize_option_data`` used to escape ``#`` in a list entry
    without normalising it, so an accented entry reached ``validate_string_space``
    unrepaired and failed a handshake that the same text in a slot name survived.
    """
    assert E.ApOption("some_option", ["ok", "café"]).value == ["ok", normalised("café")]


def test_option_list_int_entries_are_left_alone() -> None:
    # Normalising must not stringify the numbers alongside them.
    assert E.ApOption("some_option", [1, 2, 3]).value == [1, 2, 3]


def test_a_dict_option_round_trips_through_op_count() -> None:
    """``option_count`` is reachable at last.

    Two earlier shapes of this branch could not get a dict through: the first flattened it
    to its keys and lost every value, the second built a sanitised copy and fell through
    to the terminal raise without assigning it. It now commits the copy and returns.
    """
    assert E.ApOption("some_option", {"book": 7, "fairy": 2}).value == {"book": 7, "fairy": 2}


def test_a_dict_option_rejects_a_non_string_key() -> None:
    with pytest.raises(EventTypeError):
        E.ApOption("some_option", {1: 2})


def test_a_dict_option_rejects_an_unsupported_value_type() -> None:
    with pytest.raises(EventTypeError):
        E.ApOption("some_option", {"book": None})


def test_a_dict_option_rejects_whitespace_in_a_key() -> None:
    # Keys are written as bare tokens; a space would split one pair into two.
    with pytest.raises(EventValueError):
        E.ApOption("some_option", {"a b": 7})


def test_a_dict_option_key_is_normalised() -> None:
    assert E.ApOption("some_option", {"café": 7}).value == {normalised("café"): 7}



# --- accepted ---------------------------------------------------------------

def test_plain_ascii_passes() -> None:
    assert SER.serialize_event(E.SlotName("Chelshia")) == "SLOT Chelshia"


def test_full_printable_ascii_range_is_accepted() -> None:
    # The game side is being treated as able to render all of ASCII, so nothing in
    # 0x20-0x7E should be refused. Space is excluded: SLOT is a single token.
    printable = "".join(chr(c) for c in range(0x21, 0x7F))
    assert SER.serialize_event(E.SlotName(printable)).isascii()


# --- serialize_event safety net ---------------------------------------------

def test_serialized_rows_are_always_ascii() -> None:
    """Even if a validator is ever bypassed, the row that reaches disk must be ASCII."""
    event = E.SlotName("placeholder")
    object.__setattr__(event, "name", "Renée")
    assert SER.serialize_event(event).isascii()


def test_bypassed_non_ascii_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    event = E.SlotName("placeholder")
    object.__setattr__(event, "name", "Renée")
    with caplog.at_level("WARNING", logger="Client"):
        SER.serialize_event(event)
    assert any("non-ascii" in r.getMessage().lower() for r in caplog.records)
