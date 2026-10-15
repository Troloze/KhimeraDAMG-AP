# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Agent v1: the file protocol inside the sandbox folder.

The agent normally runs on its own daemon thread at 100 ms. These tests wire one by hand
(``support.fakes.make_agent``) and call a single tick method at a time, so each step of the
protocol is asserted on its own and nothing depends on timing.

Everything happens inside a temporary sandbox; see ``support/sandbox.py``.
"""

from __future__ import annotations

import time
from unittest import mock

from ...client.communication.agents import AgentV1
from ...client.communication.contracts import ContractV1
from ...client.types import RuntimeInformation
from ..support.fakes import (
    clear_flags,
    drain,
    game_message,
    make_agent,
    make_connection_context,
    make_item,
    write_flag,
)
from ..support.sandbox import RedirectedTestCase

CLIENT_OWNED = ["ap.cctx", "ap.cctx.tmp", "ap.li", "ap.li.tmp", "ap.hi", "ap.hi.tmp", "ap.gi.rd"]
GAME_OWNED = ["ap.cctx.rd", "ap.li.rd", "ap.hi.rd", "ap.gi", "ap.gi.tmp"]


class TestSandboxAccess(RedirectedTestCase):
    """``__init__`` proves it can write to the sandbox before anything else happens."""

    def test_missing_sandbox_is_created(self) -> None:
        for path in self.sandbox_root.iterdir():
            path.unlink()
        self.sandbox_root.rmdir()
        make_agent()
        self.assertTrue(self.sandbox_root.is_dir(), "the agent did not recreate the sandbox folder")

    def test_probe_files_are_cleaned_up(self) -> None:
        make_agent()
        strays = list(self.sandbox_root.glob("*.apscout"))
        self.assertEqual(strays, [], f"the access probe left {strays} behind")

    def test_unusable_sandbox_raises(self) -> None:
        # A file where the folder should be is the cheapest way to make every attempt fail. The
        # interface turns this into a message to the user, so it has to surface as an OSError
        # here rather than as a crash somewhere later in the tick.
        blocker = self.outside_root / "blocked"
        blocker.write_text("not a folder", encoding="ascii")
        with mock.patch.object(ContractV1, "get_sandbox_folder", classmethod(lambda _cls: blocker)):
            with self.assertRaises(OSError):
                AgentV1(ContractV1)


class TestFileExchange(RedirectedTestCase):
    """``_write_file``/``_read_file``: hand-off through atomic writes and ``.rd`` renames."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent()

    def test_write_creates_the_file(self) -> None:
        self.assertTrue(self.agent._write_file("ap.hi", "payload"))
        self.assertEqual((self.sandbox_root / "ap.hi").read_text(encoding="ascii"), "payload")

    def test_write_leaves_no_temporary_file(self) -> None:
        self.agent._write_file("ap.hi", "payload")
        strays = list(self.sandbox_root.glob("*.tmp"))
        self.assertEqual(strays, [], f"the write left {strays} behind")

    def test_write_refuses_to_overwrite_an_unread_document(self) -> None:
        # The game has not consumed the previous ap.hi yet, so overwriting it would lose data.
        self.agent._write_file("ap.hi", "first")
        self.assertFalse(self.agent._write_file("ap.hi", "second"))
        self.assertEqual((self.sandbox_root / "ap.hi").read_text(encoding="ascii"), "first")

    def test_status_writes_always_replace(self) -> None:
        self.agent._write_file("ap.cctx", "first")
        self.assertTrue(self.agent._write_file("ap.cctx", "second", status=True))
        self.assertEqual((self.sandbox_root / "ap.cctx").read_text(encoding="ascii"), "second")

    def test_read_consumes_the_file(self) -> None:
        (self.sandbox_root / "ap.gi").write_text("payload", encoding="ascii")
        self.assertEqual(self.agent._read_file("ap.gi"), ["payload"])
        self.assertFalse((self.sandbox_root / "ap.gi").exists(), "the consumed document was left in place")
        self.assertFalse((self.sandbox_root / "ap.gi.rd").exists(), "the .rd marker was left behind")

    def test_read_of_a_missing_file_is_empty(self) -> None:
        self.assertEqual(self.agent._read_file("ap.gi"), [])

    def test_read_recovers_a_stray_marker(self) -> None:
        # A client that died between the rename and the read leaves an ap.gi.rd behind; the
        # contract says it is recovered rather than deleted.
        (self.sandbox_root / "ap.gi.rd").write_text("older", encoding="ascii")
        self.assertEqual(self.agent._read_file("ap.gi"), ["older"])
        self.assertFalse((self.sandbox_root / "ap.gi.rd").exists())

    def test_read_returns_new_before_old(self) -> None:
        (self.sandbox_root / "ap.gi.rd").write_text("older", encoding="ascii")
        (self.sandbox_root / "ap.gi").write_text("newer", encoding="ascii")
        self.assertEqual(
            self.agent._read_file("ap.gi"),
            ["newer", "older"],
            "the fresh document has to come first, since it wins on conflicting fields"
        )

    def test_status_read_leaves_the_file_alone(self) -> None:
        (self.sandbox_root / "0.gshb").write_text("", encoding="ascii")
        self.assertEqual(self.agent._read_file("0.gshb", status=True), [""])
        self.assertTrue((self.sandbox_root / "0.gshb").exists(), "a status read must not consume the file")


class TestStartupCleanup(RedirectedTestCase):
    """KR-013: start-up cleanup must not delete game-owned files while a game is running."""

    def plant_everything(self) -> None:
        for name in CLIENT_OWNED + GAME_OWNED:
            (self.sandbox_root / name).write_text("x", encoding="ascii")
        write_flag(self.sandbox_root, "cshb", 1)
        write_flag(self.sandbox_root, "csc", 1)
        write_flag(self.sandbox_root, "gshb", 1)
        write_flag(self.sandbox_root, "gsack", 1)

    def test_no_game_running_clears_the_sandbox(self) -> None:
        agent, _htg, _gth = make_agent()
        self.plant_everything()
        agent._on_start(is_game_running=False)
        remaining = sorted(path.name for path in self.sandbox_root.iterdir())
        self.assertEqual(remaining, [], f"cleanup left {remaining} behind with no game running")

    def test_running_game_keeps_its_own_files(self) -> None:
        agent, _htg, _gth = make_agent()
        self.plant_everything()
        agent._on_start(is_game_running=True)
        remaining = {path.name for path in self.sandbox_root.iterdir()}
        for name in GAME_OWNED:
            self.assertIn(
                name,
                remaining,
                f"\"{name}\" belongs to the running game but cleanup deleted it; "
                "reconnecting would drop whatever it had written"
            )
        for name in ("1.gshb", "1.gsack"):
            self.assertIn(name, remaining, f"the running game's state flag \"{name}\" was deleted")
        for name in CLIENT_OWNED:
            self.assertNotIn(name, remaining, f"the client's own stale file \"{name}\" survived cleanup")
        self.assertNotIn("1.cshb", remaining, "the client's own heartbeat flag survived cleanup")

    def test_exit_leaves_game_owned_files(self) -> None:
        agent, _htg, _gth = make_agent()
        self.plant_everything()
        agent._on_exit()
        remaining = {path.name for path in self.sandbox_root.iterdir()}
        self.assertIn("ap.gi", remaining, "the game's pending document was deleted on exit")
        self.assertIn("1.gshb", remaining, "the game's heartbeat flag was deleted on exit")
        for name in CLIENT_OWNED:
            self.assertNotIn(name, remaining, f"\"{name}\" was left behind on exit")


class TestClientStatusFlags(RedirectedTestCase):
    """The client's own flags are single files whose name carries the value."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent()

    def flag_names(self, flag: str) -> list[str]:
        return sorted(path.name for path in self.sandbox_root.glob(f"*.{flag}"))

    def test_heartbeat_is_created_then_renamed(self) -> None:
        self.agent._send_client_status_heartbeat(1)
        self.assertEqual(self.flag_names("cshb"), ["1.cshb"])
        self.agent._send_client_status_heartbeat(2)
        self.assertEqual(
            self.flag_names("cshb"),
            ["2.cshb"],
            "the heartbeat must stay a single file; the game reads an ambiguous state as no-data"
        )

    def test_connection_flag_is_created_then_renamed(self) -> None:
        self.agent._send_client_status_connection(1)
        self.assertEqual(self.flag_names("csc"), ["1.csc"])
        self.agent._send_client_status_connection(0)
        self.assertEqual(self.flag_names("csc"), ["0.csc"])

    def test_duplicate_flags_are_collapsed(self) -> None:
        clear_flags(self.sandbox_root, "cshb")
        write_flag(self.sandbox_root, "cshb", 7)
        write_flag(self.sandbox_root, "cshb", 8)
        self.agent._send_client_status_heartbeat(9)
        self.assertEqual(
            self.flag_names("cshb"),
            ["9.cshb"],
            "a sandbox left with several heartbeat files must be collapsed back to one"
        )


class TestGameStatusFlags(RedirectedTestCase):
    """Reading the game's flags: heartbeat, ack, win and the re-request bitmask."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent()

    def mark_game_alive(self) -> None:
        # The ack, win and requirement readers all ignore a game that has not beaten recently.
        write_flag(self.sandbox_root, "gshb", 1)
        self.agent._receive_game_status_heartbeat()
        clear_flags(self.sandbox_root, "gshb")
        self.assertTrue(self.agent._is_game_alive(), "the heartbeat did not mark the game as alive")

    def test_heartbeat_marks_the_game_alive(self) -> None:
        self.assertFalse(self.agent._is_game_alive(), "a fresh agent must not consider the game alive")
        write_flag(self.sandbox_root, "gshb", 5)
        self.agent._receive_game_status_heartbeat()
        self.assertTrue(self.agent._is_game_alive())
        self.assertEqual(self.agent.last_game_heartbeat, 5)

    def test_unchanged_heartbeat_does_not_refresh_the_timer(self) -> None:
        write_flag(self.sandbox_root, "gshb", 5)
        self.agent._receive_game_status_heartbeat()
        first = self.agent.time_since_last_heartbeat_update
        time.sleep(0.01)
        self.agent._receive_game_status_heartbeat()
        self.assertEqual(
            self.agent.time_since_last_heartbeat_update,
            first,
            "the same heartbeat value must not count as a sign of life"
        )

    def test_ambiguous_heartbeat_is_ignored(self) -> None:
        write_flag(self.sandbox_root, "gshb", 1)
        write_flag(self.sandbox_root, "gshb", 2)
        self.agent._receive_game_status_heartbeat()
        self.assertEqual(
            self.agent.last_game_heartbeat,
            -1,
            "two heartbeat files are an ambiguous state and must read as no-data"
        )

    def test_ack_is_forwarded(self) -> None:
        self.mark_game_alive()
        write_flag(self.sandbox_root, "gsack", 4)
        self.agent._receive_game_status_ack()
        self.assertEqual(drain(self.gth_q), [("ack", 4)])

    def test_ack_is_ignored_while_the_game_is_not_alive(self) -> None:
        write_flag(self.sandbox_root, "gsack", 4)
        self.agent._receive_game_status_ack()
        self.assertEqual(
            drain(self.gth_q),
            [],
            "a stale flag from a closed game must not be read as a fresh ack"
        )

    def test_win_is_forwarded(self) -> None:
        self.mark_game_alive()
        write_flag(self.sandbox_root, "gswin", 1)
        self.agent._receive_game_status_win()
        self.assertEqual(drain(self.gth_q), [("is_win", 1)])

    def test_requirement_bits(self) -> None:
        # Per the contract, bit 1 asks for the context and bit 0 for the location information.
        for value, expected in (
            (0, []),
            (1, [("req_li", True)]),
            (2, [("req_cctx", True)]),
            (3, [("req_cctx", True), ("req_li", True)])
        ):
            with self.subTest(gsreq=value):
                self.mark_game_alive()
                clear_flags(self.sandbox_root, "gsreq")
                write_flag(self.sandbox_root, "gsreq", value)
                self.agent._receive_game_status_requirements()
                self.assertEqual(drain(self.gth_q), expected)

    def test_unparseable_flag_name_is_survived(self) -> None:
        self.mark_game_alive()
        (self.sandbox_root / "garbage.gsack").write_text("", encoding="ascii")
        with self.assertLogs("Client", level="WARNING"):
            self.agent._receive_game_status_ack()
        self.assertEqual(drain(self.gth_q), [], "a flag with an unreadable name must read as no-data")


class TestGameInformation(RedirectedTestCase):
    """Reading ``ap.gi``, the one document the game writes."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent(
            context=make_connection_context(slot_name="Tester")
        )

    def write_game_information(self, content: str, name: str = "ap.gi") -> None:
        (self.sandbox_root / name).write_text(content, encoding="ascii")

    def test_locations_and_acks_are_forwarded(self) -> None:
        self.write_game_information(game_message(location_ids=[11, 22], location_acks=[33], death_ack=4))
        self.agent._receive_game_information()
        received = drain(self.gth_q)
        self.assertEqual(
            sorted(entry for entry in received if entry[0] == "location"),
            [("location", 11), ("location", 22)]
        )
        self.assertIn(("location_ack", 33), received)
        self.assertIn(("death_ack", 4), received)

    def test_document_is_consumed(self) -> None:
        self.write_game_information(game_message(location_ids=[1]))
        self.agent._receive_game_information()
        self.assertFalse((self.sandbox_root / "ap.gi").exists(), "ap.gi was not consumed")

    def test_death_link_gets_the_slot_name(self) -> None:
        # The game sends a template; the client fills in who died.
        self.write_game_information(game_message(death_link={"id": 2.0, "message": "%s met a sticky end"}))
        self.agent._receive_game_information()
        received = drain(self.gth_q)
        self.assertEqual(received, [("death_link", ("Tester", 2, "Tester met a sticky end"))])

    def test_malformed_death_link_is_ignored(self) -> None:
        self.write_game_information(game_message(death_link={"id": "two", "message": None}))
        self.agent._receive_game_information()
        self.assertEqual(drain(self.gth_q), [], "a death link with the wrong field types must be dropped")

    def test_data_entries_are_forwarded(self) -> None:
        self.write_game_information(game_message(data={
            "names": ["level"],
            "types": ["NV"],
            "ids": [1.0],
            "values": [7.0],
            "count": 1.0
        }))
        self.agent._receive_game_information()
        self.assertEqual(drain(self.gth_q), [("data", (1, "level", 7.0))])

    def test_a_recovered_stray_is_merged(self) -> None:
        # Both documents are read in one go, the newer one first; locations from both must survive.
        self.write_game_information(game_message(location_ids=[1]), "ap.gi.rd")
        self.write_game_information(game_message(location_ids=[2]))
        self.agent._receive_game_information()
        locations = sorted(entry[1] for entry in drain(self.gth_q) if entry[0] == "location")
        self.assertEqual(locations, [1, 2], "a recovered stray document was dropped")

    def test_broken_document_produces_nothing(self) -> None:
        self.write_game_information("{not json")
        self.agent._receive_game_information()
        self.assertEqual(drain(self.gth_q), [])


class TestConsumer(RedirectedTestCase):
    """``_consumer`` folds the queue the client fills into one tick's worth of information."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent()

    def test_items_are_ordered_by_index(self) -> None:
        self.htg_q.put(("item", (2, make_item(222))))
        self.htg_q.put(("item", (1, make_item(111))))
        result = self.agent._consumer(0)
        self.assertIsNotNone(result)
        runtime, _status, _req = result
        self.assertEqual([index for index, _item in runtime.item_list], [1, 2])
        self.assertEqual([item.item for _index, item in runtime.item_list], [111, 222])

    def test_repeated_index_keeps_the_last_item(self) -> None:
        self.htg_q.put(("item", (1, make_item(111))))
        self.htg_q.put(("item", (1, make_item(999))))
        runtime, _status, _req = self.agent._consumer(0)
        self.assertEqual(runtime.item_list, [(1, make_item(999))])

    def test_empty_categories_stay_none(self) -> None:
        runtime, _status, _req = self.agent._consumer(0)
        self.assertIsNone(runtime.item_list)
        self.assertIsNone(runtime.locations)
        self.assertIsNone(runtime.messages)
        self.assertIsNone(runtime.data_acks)

    def test_status_and_heartbeat_are_reported(self) -> None:
        self.htg_q.put(("status", 0))
        _runtime, status, _req = self.agent._consumer(12)
        self.assertEqual(status, (0, 12), "the tick number is the client heartbeat the game watches")

    def test_requests_are_flagged_and_replace_the_context(self) -> None:
        replacement = make_connection_context(slot_name="Replaced")
        self.htg_q.put(("req_cctx", replacement))
        self.htg_q.put(("req_li", object()))
        _runtime, _status, req = self.agent._consumer(0)
        self.assertEqual(req, (True, True))
        self.assertIs(
            self.agent.connection_context,
            replacement,
            "a re-sent context must replace the one the agent holds, or the next resend is stale"
        )

    def test_stop_flag_halts_consumption(self) -> None:
        self.htg_q.put(("location", 1))
        self.agent.s_flag.set()
        self.assertIsNone(self.agent._consumer(0), "the consumer must stop as soon as the flag is raised")


class TestHostInformationWrites(RedirectedTestCase):
    """``ap.hi`` is only written when there is something to say, and is buffered when it cannot be."""

    def setUp(self) -> None:
        super().setUp()
        self.agent, self.htg_q, self.gth_q = make_agent()

    def test_nothing_to_say_writes_no_file(self) -> None:
        self.agent._send_host_information(RuntimeInformation())
        self.assertFalse(
            (self.sandbox_root / "ap.hi").exists(),
            "an empty tick must not write a document; the game reads every one it finds"
        )

    def test_content_is_written(self) -> None:
        self.agent._send_host_information(RuntimeInformation(locations={5}))
        self.assertTrue((self.sandbox_root / "ap.hi").exists())
        self.assertIsNone(self.agent.host_information_buffer, "the buffer should be cleared after a write")

    def test_unconsumed_document_is_buffered_and_merged(self) -> None:
        self.agent._send_host_information(RuntimeInformation(messages=[(1, "first")]))
        (self.sandbox_root / "ap.hi").write_text("the game has not read this yet", encoding="ascii")
        self.agent._send_host_information(RuntimeInformation(messages=[(1, "second")]))
        self.assertIsNotNone(self.agent.host_information_buffer, "the undeliverable tick was dropped")
        self.assertEqual(
            self.agent.host_information_buffer.messages,
            [(1, "second")],
            "the buffered tick lost its message"
        )
