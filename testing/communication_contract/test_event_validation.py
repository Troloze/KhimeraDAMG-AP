# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Validation and sanitisation performed by the event dataclasses themselves.

Guarding at construction means a malformed value cannot reach a serializer at all,
which is why the serializers can stay simple. These tests cover each validator and the
octothorpe escaping the spec requires:

    "Due to GameMaker limitations, all instances of an octothorpe (#) should be
     preceded by a backslash."

The validators raise ``EventValueError`` / ``EventTypeError`` rather than the builtins, so
the deserializers can drop a single bad row instead of discarding a whole document. Note
that ``EventValueError`` subclasses ``TypeError``, not ``ValueError`` -- these tests name
the classes explicitly rather than relying on either builtin.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import ContractV1, EventSerializer, EventTypeError, EventValueError, rows

SER = EventSerializer
BS = chr(92)


# --- validate_version -------------------------------------------------------

@pytest.mark.parametrize("version", ["0.0.0", "0.6.7", "10.20.30", "999.0.1"])
def test_valid_versions_are_accepted(version: str) -> None:
    assert E.ApVersion(version).version == version


@pytest.mark.parametrize("version", ["", "1", "1.2", "1.2.3.4", "1..3", "x.y.z", "1.2.z", "-1.0.0", "1.-2.3"])
def test_malformed_versions_raise_value_error(version: str) -> None:
    with pytest.raises(EventValueError):
        E.ApVersion(version)


def test_version_error_message_is_diagnosable() -> None:
    # A raw "invalid literal for int()" tells a user nothing about the contract.
    with pytest.raises(EventValueError) as excinfo:
        E.ApVersion("x.y.z")
    assert "X.Y.Z" in str(excinfo.value), f"unhelpful message: {excinfo.value}"


# --- validate_int_non_negative ----------------------------------------------

@pytest.mark.parametrize("factory", [
    pytest.param(lambda v: E.LastAck(v), id="LastAck"),
    pytest.param(lambda v: E.LocationChecked(v), id="LocationChecked"),
    pytest.param(lambda v: E.Ack(v), id="Ack"),
    pytest.param(lambda v: E.Heartbeat(v), id="Heartbeat"),
    pytest.param(lambda v: E.ItemReceived(v, 1), id="ItemReceived.item_id"),
    pytest.param(lambda v: E.ItemReceived(1, v), id="ItemReceived.order_received"),
    pytest.param(lambda v: E.LocationClassification(v, 1, 1), id="LocationClassification.location_id"),
    pytest.param(lambda v: E.LocationClassification(1, v, 1), id="LocationClassification.classification"),
    pytest.param(lambda v: E.LocationClassification(1, 1, v), id="LocationClassification.player_id"),
])
def test_negative_values_are_rejected(factory) -> None:
    factory(0)  # zero must remain valid
    with pytest.raises(EventValueError):
        factory(-1)


# --- validate_bool ----------------------------------------------------------

@pytest.mark.parametrize("factory", [
    pytest.param(lambda v: E.ConnectionStatus(v), id="ConnectionStatus"),
    pytest.param(lambda v: E.LocationClassificationPreview(v), id="LocationClassificationPreview"),
])
def test_boolean_fields_accept_only_zero_and_one(factory) -> None:
    factory(0)
    factory(1)
    for bad in (-1, 2, 100):
        with pytest.raises(EventValueError):
            factory(bad)


# --- validate_option_data ---------------------------------------------------

def test_option_value_rejects_whitespace_in_strings() -> None:
    with pytest.raises(EventValueError):
        E.ApOption("some_option", "two words")


def test_option_list_rejects_whitespace_in_strings() -> None:
    with pytest.raises(EventValueError):
        E.ApOption("some_option", ["ok", "two words"])


def test_option_list_rejects_unsupported_element_types() -> None:
    with pytest.raises((EventTypeError, EventValueError)):
        E.ApOption("some_option", ["ok", None])


def test_option_value_rejects_unsupported_types() -> None:
    # The declared type is int | str | list | dict; anything else must not slip through
    # to a serializer that will f-string it into the row. A dict is supported now, so the
    # probes here are types with no wire representation at all.
    for value in (3.5, None, object(), (1, 2)):
        with pytest.raises((EventTypeError, EventValueError)):
            E.ApOption("some_option", value)



def test_option_name_rejects_whitespace() -> None:
    with pytest.raises(EventValueError):
        E.ApOption("two words", 1)


# --- octothorpe escaping ----------------------------------------------------

def test_slot_name_escapes_the_octothorpe() -> None:
    assert E.SlotName("Player#1").name == f"Player{BS}#1"


def test_slot_name_escapes_every_occurrence() -> None:
    assert E.SlotName("#a#b#").name == f"{BS}#a{BS}#b{BS}#"


def test_message_escapes_the_octothorpe() -> None:
    assert E.Message("got item #3").message == f"got item {BS}#3"


def test_deathlink_escapes_the_octothorpe() -> None:
    assert E.DeathLink("squashed by #7").message == f"squashed by {BS}#7"


def test_option_string_value_escapes_the_octothorpe() -> None:
    assert E.ApOption("some_option", "a#b").value == f"a{BS}#b"


def test_option_list_values_escape_the_octothorpe() -> None:
    assert E.ApOption("some_option", ["a#b", "c"]).value == [f"a{BS}#b", "c"]


def test_slot_data_string_value_escapes_the_octothorpe() -> None:
    assert E.SlotData("some_data", "a#b").value == f"a{BS}#b"


def test_escaped_octothorpe_reaches_the_serialized_row() -> None:
    assert rows(ContractV1.parse_events([E.SlotName("Player#1")])) == [f"SLOT Player{BS}#1"]


def test_message_with_octothorpe_reaches_the_serialized_row() -> None:
    assert rows(ContractV1.parse_events([E.Message("hi #1")])) == [f"MSG hi {BS}#1"]


# --- messages keep their spaces, but not their line breaks ------------------

def test_message_keeps_interior_spaces() -> None:
    # MSG is a greedy tail, so spaces are meaningful and must survive.
    assert E.Message("Vitor sent Fire Gauntlet").message == "Vitor sent Fire Gauntlet"


# Row-breaking characters are stripped rather than rejected: a message is display
# text, so dropping a newline is preferable to refusing the whole write. Space is
# deliberately preserved, since MSG and DLINK are greedy tails.
# Built from code points so no editor or tooling can rewrite them in transit.
# These are exactly the ASCII characters str.splitlines() treats as row breaks.
LINE_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E)]


@pytest.mark.parametrize("ch", LINE_BREAKS, ids=lambda c: f"U+{ord(c):04X}")
def test_message_strips_row_breaking_characters(ch: str) -> None:
    assert E.Message(f"two{ch}lines").message == "twolines"


@pytest.mark.parametrize("ch", LINE_BREAKS, ids=lambda c: f"U+{ord(c):04X}")
def test_deathlink_strips_row_breaking_characters(ch: str) -> None:
    assert E.DeathLink(f"two{ch}lines").message == "twolines"


@pytest.mark.parametrize("ch", LINE_BREAKS, ids=lambda c: f"U+{ord(c):04X}")
def test_slot_name_strips_row_breaking_characters(ch: str) -> None:
    assert E.SlotName(f"two{ch}lines").name == "twolines"


@pytest.mark.parametrize("ch", LINE_BREAKS, ids=lambda c: f"U+{ord(c):04X}")
def test_a_sanitised_message_stays_on_one_row(ch: str) -> None:
    # The invariant that actually matters: whatever survives must not split the row,
    # measured with splitlines() because that is what the reader uses.
    assert len(rows(ContractV1.parse_events([E.Message(f"two{ch}lines")]))) == 1


def test_tabs_are_stripped_but_spaces_survive() -> None:
    assert E.Message("a" + chr(9) + "b c").message == "ab c"
