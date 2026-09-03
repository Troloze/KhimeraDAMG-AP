# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""How a future contract version extends this one.

The serializer classes now dispatch through ``cls`` (``OptionSerializer.serialize``
reads ``cls.types``), so subclassing *them* works. The chain above them is still module
level, though: ``ContractV1.parse_events`` calls the module's ``EventSerializer``, which
names ``OptionSerializer`` directly. Subclassing ``ContractV1`` therefore does **not**
redirect serialization -- a V2 module subclasses the serializers and rewires its own
contract class instead.

These tests pin both halves of that: the pieces a V2 needs are genuinely extensible, and
the inheritance route that looks like it should work is documented as not working, so the
limitation is caught by the suite rather than discovered during a V2 port.
"""

from __future__ import annotations

import pytest

from harness import CommunicationEvent as E
from harness import (
    ContractV1,
    DataSerializer,
    EventDeserializer,
    EventSerializer,
    OptionSerializer,
    rows,
)


# --- the pieces a V2 module would extend ------------------------------------

class OptionSerializerV2(OptionSerializer):
    """A hypothetical next version that teaches the contract one new option."""

    types = {
        **OptionSerializer.types,
        "shuffle_hats": "toggle",
    }


class EventDeserializerV2(EventDeserializer):
    """A hypothetical next version that teaches the reader one new identifier."""

    @staticmethod
    def deserialize_ping(row: list[str]) -> E.Heartbeat | None:
        if len(row) <= 1:
            return None
        return E.Heartbeat(int(row[1]))

    flag_to_parser = {
        **EventDeserializer.flag_to_parser,
        "PING": "deserialize_ping",
    }


def test_option_tables_are_class_level_and_inheritable() -> None:
    # If these ever move back to module globals, a V2 cannot extend them without
    # mutating V1's own table in the same process.
    assert "types" in vars(OptionSerializer)
    assert "serializers" in vars(OptionSerializer)
    assert "types" in vars(DataSerializer)
    assert "serializers" in vars(DataSerializer)


def test_option_dispatch_resolves_through_cls() -> None:
    """serialize is a classmethod reading cls.types, so a subclass redirects it.

    The old name-keyed delegate_serialize took a literal "Option"/"Data" and looked the
    class up in a fixed table, which meant a subclass could never be routed to. Dispatch
    now goes through ``cls``, so the subclass route below actually works.
    """
    assert OptionSerializer.serialize("victory_condition", 2) == "OPTION victory_condition S 2"


def test_a_subclass_table_is_a_copy_not_a_shared_dict() -> None:
    assert "shuffle_hats" in OptionSerializerV2.types
    assert "shuffle_hats" not in OptionSerializer.types


def test_a_subclass_can_serialize_an_option_its_parent_rejects() -> None:
    # The payoff of cls-based dispatch: no mutation of V1's table, no parallel dispatcher.
    assert OptionSerializerV2.serialize("shuffle_hats", 1) == "OPTION shuffle_hats S 1"
    assert OptionSerializer.serialize("shuffle_hats", 1) == ""


def test_the_subclass_inherits_the_serializer_methods() -> None:
    assert OptionSerializerV2.toggle(("shuffle_hats", 1)) == "OPTION shuffle_hats S 1"


def test_unknown_options_are_dropped_not_raised() -> None:
    assert OptionSerializer.serialize("shuffle_hats", 1) == ""


def test_subclass_can_add_a_new_identifier_to_the_reader() -> None:
    assert EventDeserializerV2.deserialize_line("PING 7") == E.Heartbeat(7)


def test_v1_does_not_know_the_new_identifier() -> None:
    events, _ = ContractV1.parse_message("PING 7\n$")
    assert events == []


def test_v1_does_not_know_the_new_option() -> None:
    assert rows(ContractV1.parse_events([E.ApOption("shuffle_hats", 1)])) == []


# --- the limitation a V2 port has to work around ----------------------------

def test_contract_subclassing_does_not_redirect_serialization() -> None:
    """Documented gap: ContractV1's dispatch is module level, not ``cls`` based.

    Overriding the nested name on a subclass has no effect, because
    ``ContractV1.parse_events`` resolves ``EventSerializer`` from module globals. A V2
    that wants different serialization must define its own contract class body rather
    than inherit ``parse_events``.
    """

    class ContractV2(ContractV1):
        OptionSerializer = OptionSerializerV2
        EventSerializer = EventSerializer

    assert rows(ContractV2.parse_events([E.ApOption("shuffle_hats", 1)])) == [], (
        "ContractV1 now dispatches through cls; update the V2 guidance in this module"
    )
