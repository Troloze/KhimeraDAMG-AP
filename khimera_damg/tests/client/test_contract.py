# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Contract v1: the document shapes the game reads, and the validators that guard them.

``docs/Communication Contract v1.md`` is the governing specification, so the field names asserted
here are quoted from it. The mod reads these exact keys: KR-009 (``data_acks`` vs ``data_ack``)
and KR-020 (``generation_information`` vs ``generation_info``) were both a single renamed key.
"""

from __future__ import annotations

import json
import unittest
from typing import Any

from ...client.communication.contracts.contract_v1 import (
    ContractV1,
    OptionDataHandler,
    normalize_number,
    validate_bool,
    validate_int_non_negative,
    validate_list,
    validate_version,
)
from ...client.communication.misc import normalize_and_sanitize
from ...client.types import RuntimeInformation
from ..support.fakes import game_message, make_connection_context, make_item, make_location_information


def message_of(written: tuple[str, int]) -> dict[str, Any]:
    """The message dict out of a ``write_content`` result."""
    content, exit_code = written
    assert exit_code == 0, f"write_content reported exit code {exit_code}"
    return json.loads(content)["message"]


class TestValidators(unittest.TestCase):
    """The small guards every writer runs before it serialises anything."""

    def test_version_accepts_three_numbers(self) -> None:
        for version in ("0.0.0", "0.0.9", "10.20.30"):
            with self.subTest(version=version):
                validate_version(version)

    def test_version_rejects_everything_else(self) -> None:
        for version in ("1.0", "1.0.0.0", "a.b.c", "", "1..0", "-1.0.0", "0.0.9-beta"):
            with self.subTest(version=version):
                with self.assertRaises(ValueError, msg=f"\"{version}\" was accepted as a version"):
                    validate_version(version)

    def test_non_negative(self) -> None:
        validate_int_non_negative(0)
        validate_int_non_negative(17)
        with self.assertRaises(ValueError):
            validate_int_non_negative(-1)

    def test_bool_is_zero_or_one(self) -> None:
        validate_bool(0)
        validate_bool(1)
        for value in (-1, 2, 100):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_bool(value)

    def test_lists_must_be_homogeneous(self) -> None:
        validate_list([])
        validate_list([1])
        validate_list([1, 2, 3])
        validate_list(["a", "b"])
        with self.assertRaises(TypeError):
            validate_list([1, "two"])

    def test_whole_floats_become_ints(self) -> None:
        # GameMaker has one number type, so an integer arrives as 1.0 and has to be written back
        # as 1; see KR-027.
        self.assertEqual(normalize_number(1.0), 1)
        self.assertIsInstance(normalize_number(1.0), int)
        self.assertEqual(normalize_number(1.5), 1.5)
        self.assertEqual(normalize_number(3), 3)


class TestNormalisation(unittest.TestCase):
    """``normalize_and_sanitize`` makes any text safe for the game's ASCII-only reader."""

    def test_ascii_passes_through(self) -> None:
        self.assertEqual(normalize_and_sanitize("Plain text 123!"), "Plain text 123!")

    def test_control_characters_are_stripped(self) -> None:
        self.assertEqual(normalize_and_sanitize("a\x00b\x1fc\x7fd"), "abcd")

    def test_known_characters_are_translated(self) -> None:
        self.assertEqual(normalize_and_sanitize("\u201cquoted\u201d"), "\"quoted\"")
        self.assertEqual(normalize_and_sanitize("don\u2019t"), "don't")
        self.assertEqual(normalize_and_sanitize("a\u2026b"), "a...b")

    def test_accents_are_folded(self) -> None:
        self.assertEqual(normalize_and_sanitize("Spa\u00eectre Die"), "Spaictre Die")

    def test_unknown_characters_use_the_replacement(self) -> None:
        self.assertEqual(normalize_and_sanitize("\u3042", "?"), "?")
        self.assertEqual(normalize_and_sanitize("\u3042"), "_")

    def test_result_is_always_ascii(self) -> None:
        for text in ("\u2014 dash", "\u00e9l\u00e8ve", "\u65e5\u672c\u8a9e", "mixed \u2013 \u00fcber"):
            with self.subTest(text=text):
                self.assertTrue(normalize_and_sanitize(text).isascii(), f"\"{text}\" did not fold to ASCII")


class TestOptionFormatting(unittest.TestCase):
    """Options are sent as parallel name/type/value lists with a count."""

    def test_known_options_are_kept(self) -> None:
        formatted = OptionDataHandler.format_option({"death_link": 1, "shuffle_books": 0})
        self.assertEqual(formatted["count"], 2)
        self.assertEqual(
            dict(zip(formatted["names"], formatted["values"], strict=True)),
            {"death_link": 1, "shuffle_books": 0}
        )
        self.assertEqual(set(formatted["types"]), {"NV"})

    def test_unknown_options_are_dropped(self) -> None:
        # An option the game does not know about must not reach it as a half-typed entry.
        # The handler logs each unknown name once per process, so every test here uses a name of
        # its own; assertLogs both proves the warning and keeps it out of the test output.
        with self.assertLogs("Client", level="WARNING"):
            formatted = OptionDataHandler.format_option({"death_link": 1, "not_an_option": "???"})
        self.assertEqual(formatted["names"], ["death_link"])
        self.assertEqual(formatted["count"], 1)

    def test_parallel_lists_stay_aligned(self) -> None:
        formatted = OptionDataHandler.format_option({"death_link": 1, "victory_condition": 0, "shuffle_fairies": 1})
        self.assertEqual(len(formatted["names"]), formatted["count"])
        self.assertEqual(len(formatted["types"]), formatted["count"])
        self.assertEqual(len(formatted["values"]), formatted["count"])


class TestDataFormatting(unittest.TestCase):
    """Game data is typed by inspection, since the game decides what it stores."""

    def test_types_are_derived_from_the_value(self) -> None:
        formatted = OptionDataHandler.format_data({
            "text": "value",
            "number": 3,
            "numbers": [1, 2],
            "texts": ["a", "b"],
            "mapping": {"inner": 1}
        })
        by_name = dict(zip(formatted["names"], formatted["types"], strict=True))
        self.assertEqual(
            by_name,
            {"text": "SV", "number": "NV", "numbers": "NL", "texts": "SL", "mapping": "D"},
            f"types were derived as {by_name}"
        )

    def test_whole_floats_are_normalised_everywhere(self) -> None:
        formatted = OptionDataHandler.format_data({
            "scalar": 2.0,
            "list": [1.0, 2.5],
            "mapping": {"inner": 4.0}
        })
        values = dict(zip(formatted["names"], formatted["values"], strict=True))
        self.assertEqual(values["scalar"], 2)
        self.assertIsInstance(values["scalar"], int)
        self.assertEqual(values["list"], [1, 2.5])
        self.assertEqual(values["mapping"], {"inner": 4})

    def test_empty_list_is_sent_as_a_number_list(self) -> None:
        formatted = OptionDataHandler.format_data({"empty": []})
        self.assertEqual(formatted["types"], ["NL"])

    def test_unsupported_values_are_dropped(self) -> None:
        with self.assertLogs("Client", level="WARNING"):
            formatted = OptionDataHandler.format_data({"good": 1, "bad_scalar": object()})
        self.assertEqual(formatted["names"], ["good"])
        self.assertEqual(formatted["count"], 1)

    def test_dictionary_values_are_filtered(self) -> None:
        with self.assertLogs("Client", level="WARNING"):
            formatted = OptionDataHandler.format_data({"mapping": {"keep": "text", "drop": object()}})
        self.assertEqual(formatted["values"], [{"keep": "text"}])

    def test_text_is_normalised(self) -> None:
        formatted = OptionDataHandler.format_data({"name": "Spa\u00eectre"})
        self.assertEqual(formatted["values"], ["Spaictre"])


class TestDataReading(unittest.TestCase):
    """``read_data`` turns the game's parallel lists back into (id, name, value) tuples."""

    def payload(self, **overrides: Any) -> dict[str, Any]:
        data = {
            "names": ["level", "label", "list"],
            "types": ["NV", "SV", "NL"],
            "ids": [1.0, 2.0, 3.0],
            "values": [3.0, "text", [1.0, 2.0]],
            "count": 3.0
        }
        data.update(overrides)
        return data

    def test_round_trip(self) -> None:
        read = OptionDataHandler.read_data(self.payload())
        self.assertEqual(
            read,
            [(1, "level", 3.0), (2, "label", "text"), (3, "list", [1.0, 2.0])],
            f"read_data returned {read}"
        )

    def test_ids_and_count_are_coerced_to_int(self) -> None:
        # Every number the game sends arrives as a float, including ids and the count.
        read = OptionDataHandler.read_data(self.payload())
        for entry_id, _name, _value in read:
            self.assertIsInstance(entry_id, int, f"id {entry_id!r} was not coerced to int")

    def test_removal_type_clears_the_value(self) -> None:
        read = OptionDataHandler.read_data(self.payload(
            names=["gone"],
            types=["RM"],
            ids=[9.0],
            values=["ignored"],
            count=1.0
        ))
        self.assertEqual(read, [(9, "gone", None)], "an RM entry must read back as a removal")

    def test_malformed_payload_is_dropped(self) -> None:
        with self.assertLogs("Client", level="WARNING"):
            read = OptionDataHandler.read_data(self.payload(values=[1.0]))
        self.assertEqual(read, [], "a payload with mismatched list lengths must be discarded")

    def test_count_limits_how_much_is_read(self) -> None:
        read = OptionDataHandler.read_data(self.payload(count=1.0))
        self.assertEqual(len(read), 1, "read_data ignored the count field")


class TestConnectionContextDocument(unittest.TestCase):
    """``ap.cctx``: everything the game needs to resume a slot."""

    def test_meta_fields(self) -> None:
        context = make_connection_context(slot_name="Tester", seed="12345")
        meta = message_of(ContractV1.write_content("cctx", context.to_dict()))["meta"]
        self.assertEqual(
            set(meta),
            {
                "archipelago_version",
                "host_world_version",
                "client_world_version",
                "slot_name",
                "seed",
                "options",
                "generation_information"
            },
            f"cctx meta fields are {sorted(meta)}"
        )
        self.assertEqual(meta["slot_name"], "Tester")
        self.assertEqual(meta["seed"], "12345")

    def test_session_is_minimal_when_there_is_nothing_to_say(self) -> None:
        session = message_of(ContractV1.write_content("cctx", make_connection_context().to_dict()))["session"]
        self.assertEqual(
            set(session),
            {"last_ack"},
            f"an empty session carried {sorted(session)}; optional keys should be omitted entirely"
        )

    def test_session_carries_items_locations_and_goal(self) -> None:
        context = make_connection_context(
            last_ack=2,
            locations=({11, 22}),
            item_list=[(2, make_item(222)), (1, make_item(111))],
            has_goaled=True,
            game_data={"level": 3}
        )
        session = message_of(ContractV1.write_content("cctx", context.to_dict()))["session"]
        self.assertEqual(session["last_ack"], 2)
        self.assertEqual(session["is_win"], 1, "has_goaled must be sent as 1")
        self.assertEqual(sorted(session["location_ids"]), [11, 22])
        self.assertEqual(session["game_data"]["names"], ["level"])
        # The item list is indexed from 1 by the game, so index 0 holds a sentinel.
        self.assertEqual(
            session["item_list"]["item_ids"],
            [-1, 111, 222],
            "items must be ordered by their index, behind the -1 sentinel"
        )
        self.assertEqual(session["item_list"]["count"], 2)

    def test_resync_marker_is_allowed(self) -> None:
        # -1 is the documented "resend everything" value, and is the one negative ack accepted.
        context = make_connection_context(last_ack=-1)
        session = message_of(ContractV1.write_content("cctx", context.to_dict()))["session"]
        self.assertEqual(session["last_ack"], -1)

    def test_negative_ack_is_rejected(self) -> None:
        context = make_connection_context(last_ack=-2)
        with self.assertRaises(ValueError):
            ContractV1.write_content("cctx", context.to_dict())

    def test_version_fields_are_validated(self) -> None:
        context = make_connection_context(host_world_version="not a version")
        with self.assertRaises(ValueError):
            ContractV1.write_content("cctx", context.to_dict())

    def test_text_fields_are_normalised(self) -> None:
        context = make_connection_context(slot_name="Pl\u00e4yer\x00")
        meta = message_of(ContractV1.write_content("cctx", context.to_dict()))["meta"]
        self.assertEqual(meta["slot_name"], "Player")


class TestLocationInformationDocument(unittest.TestCase):
    """``ap.li``: per-location item information, withheld in race mode."""

    def test_disabled_sends_an_empty_table(self) -> None:
        message = message_of(ContractV1.write_content(
            "li",
            make_location_information(False, {1: (2, 3)}).to_dict()
        ))
        self.assertEqual(message["enabled"], 0)
        self.assertEqual(message["locations"]["count"], 0)
        self.assertEqual(message["locations"]["location_ids"], [], "race mode leaked location information")

    def test_enabled_sends_parallel_lists(self) -> None:
        info = make_location_information(True, {100: (1, 2), 200: (0, 1)})
        message = message_of(ContractV1.write_content("li", info.to_dict()))
        self.assertEqual(message["enabled"], 1)
        locations = message["locations"]
        self.assertEqual(locations["count"], 2)
        self.assertEqual(
            dict(zip(
                locations["location_ids"],
                zip(locations["location_classifications"], locations["player_ids"], strict=True),
                strict=True
            )),
            {100: (1, 2), 200: (0, 1)}
        )

    def test_negative_entries_are_rejected(self) -> None:
        info = make_location_information(True, {-1: (1, 2)})
        with self.assertRaises(ValueError):
            ContractV1.write_content("li", info.to_dict())

    def test_non_numeric_entries_are_rejected(self) -> None:
        info = make_location_information(True, {1: ("classification", 2)})  # type: ignore[dict-item]
        with self.assertRaises(ValueError):
            ContractV1.write_content("li", info.to_dict())


class TestHostInformationDocument(unittest.TestCase):
    """``ap.hi``: everything that happened on the server since the last tick."""

    def test_empty_runtime_information_writes_an_empty_message(self) -> None:
        message = message_of(ContractV1.write_content("hi", RuntimeInformation().to_dict()))
        self.assertEqual(message, {}, f"an empty tick produced {message}")

    def test_field_names_match_the_specification(self) -> None:
        # These are the keys the mod looks up. KR-009 was "data_acks" being read as "data_ack".
        runtime = RuntimeInformation(
            item_list=[(1, make_item(111))],
            locations={5},
            messages=[(1, "hello")],
            data_acks=[7],
            death_link=("Tester", 3, "%s died"),
            death_ack=2
        )
        message = message_of(ContractV1.write_content("hi", runtime.to_dict()))
        self.assertEqual(
            set(message),
            {"messages", "death_link", "item_list", "location_ids", "death_ack", "data_acks"},
            f"ap.hi carried {sorted(message)}"
        )
        self.assertEqual(message["data_acks"], [7])
        self.assertEqual(message["death_ack"], 2)
        self.assertEqual(sorted(message["location_ids"]), [5])

    def test_item_list_keeps_its_indexes(self) -> None:
        runtime = RuntimeInformation(item_list=[(4, make_item(111, player=3))])
        item_list = message_of(ContractV1.write_content("hi", runtime.to_dict()))["item_list"]
        self.assertEqual(item_list["item_ids"], [111])
        self.assertEqual(item_list["player_ids"], [3])
        self.assertEqual(item_list["item_indexes"], [4], "the game needs the index to ack items")
        self.assertEqual(item_list["count"], 1)

    def test_death_link_fields(self) -> None:
        runtime = RuntimeInformation(death_link=("Sender", 9, "Sender died"))
        death_link = message_of(ContractV1.write_content("hi", runtime.to_dict()))["death_link"]
        self.assertEqual(
            set(death_link),
            {"sender", "death_id", "message"},
            f"death_link carried {sorted(death_link)}"
        )
        self.assertEqual(death_link["death_id"], 9)

    def test_messages_are_normalised(self) -> None:
        runtime = RuntimeInformation(messages=[(1, "found \u201cFairy\u201d")])
        messages = message_of(ContractV1.write_content("hi", runtime.to_dict()))["messages"]
        self.assertEqual(messages["messages"], ["found \"Fairy\""])
        self.assertEqual(messages["senders"], [1])
        self.assertEqual(messages["count"], 1)


class TestStateFlags(unittest.TestCase):
    """State flags are file *names*: ``<value>.<flag>``."""

    def test_writing_a_flag(self) -> None:
        name, exit_code = ContractV1.write_content("cshb", {"flag": "cshb", "value": 12})
        self.assertEqual(name, "12.cshb")
        self.assertEqual(exit_code, 0)

    def test_reading_a_flag(self) -> None:
        for flag in ("gshb", "gsreq", "gsack", "gswin"):
            with self.subTest(flag=flag):
                self.assertEqual(ContractV1.read_content(flag, f"7.{flag}")["message"], "7")

    def test_round_trip(self) -> None:
        name, _ = ContractV1.write_content("csc", {"flag": "csc", "value": 1})
        self.assertEqual(ContractV1.read_content("gshb", name)["message"], "1")


class TestGameInformationReading(unittest.TestCase):
    """``ap.gi`` is written by the game, so every shape has to be survivable."""

    def test_valid_message_is_returned(self) -> None:
        read = ContractV1.read_content("gi", game_message(location_ids=[1, 2], death_ack=3))
        self.assertEqual(read["message"]["location_ids"], [1, 2])
        self.assertEqual(read["exit_code"], 0)

    def test_data_is_parsed_in_place(self) -> None:
        read = ContractV1.read_content("gi", game_message(data={
            "names": ["level"],
            "types": ["NV"],
            "ids": [1.0],
            "values": [2.0],
            "count": 1.0
        }))
        self.assertEqual(read["message"]["data"], [(1, "level", 2.0)])

    def test_broken_json_reads_as_no_message(self) -> None:
        read = ContractV1.read_content("gi", "{not json")
        self.assertIsNone(read["message"])
        self.assertEqual(read["exit_code"], 1, "a broken document must report a failure exit code")

    def test_wrong_shapes_read_as_no_message(self) -> None:
        for content in ("[]", "{}", json.dumps({"message": "not a dict"}), json.dumps({"other": {}})):
            with self.subTest(content=content):
                self.assertIsNone(ContractV1.read_content("gi", content)["message"])


class TestContractSurface(unittest.TestCase):
    """The dispatch tables, and the sandbox location itself."""

    def test_unknown_content_types_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            ContractV1.write_content("nonsense", {})
        with self.assertRaises(ValueError):
            ContractV1.read_content("nonsense", "")

    def test_writers_and_readers_cover_the_contract(self) -> None:
        self.assertEqual(
            set(ContractV1.type_to_writer),
            {"cctx", "li", "hi", "cshb", "csc"},
            "the client writes exactly the documents and flags the contract assigns to it"
        )
        self.assertEqual(
            set(ContractV1.type_to_reader),
            {"gi", "gsreq", "gshb", "gsack", "gswin"},
            "the client reads exactly the documents and flags the game owns"
        )

    def test_sandbox_folder_is_the_documented_one(self) -> None:
        # Not redirected here on purpose: this asserts the real location the contract names.
        # Computing the path creates nothing.
        self.assertEqual(ContractV1.get_sandbox_folder().name, "khimera_ap")

    def test_event_round_trip(self) -> None:
        content, _ = ContractV1.parse_events({"a": 1})
        parsed, exit_code = ContractV1.parse_message(content)
        self.assertEqual(parsed, {"message": {"a": 1}})
        self.assertEqual(exit_code, 0)
