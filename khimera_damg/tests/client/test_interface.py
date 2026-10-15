# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The asyncio-to-thread interface, its stop flag, and the agent registry.

``StopFlag`` replaced the ``queue.ShutDown`` API the client used to rely on, which only exists
from Python 3.13 (KR-008). It is the one piece of synchronisation between the client's event
loop and the agent thread, so its contract is worth pinning.
"""

from __future__ import annotations

import queue
import unittest

from ...client.communication import KhimeraDAMGCommunicationInterface
from ...client.communication.agents import AgentV1
from ...client.communication.classes import StopFlag
from ...client.communication.contract_storage import get_agent
from ...client.communication.contracts import ContractV1
from ..support.fakes import drain, make_connection_context, make_item, make_location_information


class TestStopFlag(unittest.TestCase):
    """A lock plus a flag: readers hold the lock while they decide what to do."""

    def test_starts_clear(self) -> None:
        self.assertFalse(StopFlag().value)

    def test_set_is_visible(self) -> None:
        flag = StopFlag()
        flag.set()
        self.assertTrue(flag.value)

    def test_context_manager_reports_the_current_value(self) -> None:
        flag = StopFlag()
        with flag as raised:
            self.assertFalse(raised)
        flag.set()
        with flag as raised:
            self.assertTrue(raised)

    def test_setting_while_held_is_refused(self) -> None:
        # The holder is mid-decision; letting the flag move under it is what the lock prevents.
        flag = StopFlag()
        with self.assertRaises(RuntimeError):
            with flag:
                flag.set()

    def test_the_lock_is_released_after_use(self) -> None:
        flag = StopFlag()
        with flag:
            pass
        flag.set()
        self.assertTrue(flag.value)


class TestAgentRegistry(unittest.TestCase):
    """``get_agent`` maps a host world version onto the agent and contract to speak."""

    def test_known_version_builds_an_agent_factory(self) -> None:
        factory = get_agent("0.0.0")
        self.assertIs(factory.func, AgentV1)
        self.assertEqual(factory.args, (ContractV1,))

    def test_newer_versions_fall_back_to_the_highest_match(self) -> None:
        # Any future world version keeps working with the newest contract the client knows.
        self.assertIs(get_agent("9.9.9").func, AgentV1)

    def test_malformed_versions_are_refused(self) -> None:
        for version in ("1.0", "1.0.0.0", "a.b.c"):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    get_agent(version)

    def test_versions_below_the_first_contract_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            get_agent("-1.0.0")


class TestInterfaceSending(unittest.TestCase):
    """What the client puts on the queue the agent thread drains."""

    def setUp(self) -> None:
        self.interface = KhimeraDAMGCommunicationInterface()

    def sent(self) -> list[tuple[str, object]]:
        return drain(self.interface._send_queue)

    def test_items_carry_their_index(self) -> None:
        self.interface.send_items([(1, make_item(111)), (2, make_item(222))])
        self.assertEqual(self.sent(), [("item", (1, make_item(111))), ("item", (2, make_item(222)))])

    def test_locations_are_sent_individually(self) -> None:
        self.interface.send_locations({5})
        self.assertEqual(self.sent(), [("location", 5)])

    def test_data_acks_are_sent_individually(self) -> None:
        self.interface.send_data_acks([1, 2])
        self.assertEqual(self.sent(), [("data_ack", 1), ("data_ack", 2)])

    def test_connection_status_is_sent_as_a_number(self) -> None:
        self.interface.send_connection_status(True)
        self.interface.send_connection_status(False)
        self.assertEqual(self.sent(), [("status", 1), ("status", 0)])

    def test_death_links_and_acks(self) -> None:
        self.interface.send_death_link("Tester", 3, "died")
        self.interface.send_death_ack(3)
        self.assertEqual(self.sent(), [("death_link", ("Tester", 3, "died")), ("death_ack", 3)])

    def test_documents_are_queued_as_requests(self) -> None:
        context = make_connection_context()
        info = make_location_information()
        self.interface.send_connection_context(context)
        self.interface.send_location_information(info)
        self.assertEqual(self.sent(), [("req_cctx", context), ("req_li", info)])

    def test_nothing_is_queued_once_stopped(self) -> None:
        # After the flag is raised the agent is on its way out; queueing more would leak work
        # that nobody will ever read.
        self.interface.stop_flag.set()
        self.interface.send_location(1)
        self.interface.send_message(1, "hello")
        self.interface.send_death_ack(1)
        self.assertEqual(self.sent(), [], "work was queued after the interface was stopped")


class TestInterfaceConsuming(unittest.TestCase):
    """``consume_outgoing`` folds what the agent reported into one package for the client."""

    def setUp(self) -> None:
        self.interface = KhimeraDAMGCommunicationInterface()

    def put(self, *entries: tuple[str, object]) -> None:
        for entry in entries:
            self.interface._get_queue.put(entry)

    def test_locations_and_acks_are_gathered(self) -> None:
        self.put(("location", 1), ("location", 2), ("location_ack", 1))
        package = self.interface.consume_outgoing()
        self.assertEqual(package.locations, {1, 2})
        self.assertEqual(package.location_acks, {1})

    def test_empty_queue_reports_nothing_pending(self) -> None:
        package = self.interface.consume_outgoing()
        self.assertIsNone(package.locations)
        self.assertIsNone(package.location_acks)
        self.assertIsNone(package.death_link)
        self.assertIsNone(package.req_cctx)
        self.assertEqual(package.ack, 0)

    def test_the_session_ack_only_moves_forward(self) -> None:
        self.put(("ack", 5))
        self.assertEqual(self.interface.consume_outgoing().ack, 5)
        self.put(("ack", 2))
        self.assertEqual(
            self.interface.consume_outgoing().ack,
            5,
            "a stale ack from the game lowered the session value"
        )

    def test_the_ack_is_remembered_across_ticks(self) -> None:
        self.put(("ack", 4))
        self.interface.consume_outgoing()
        self.assertEqual(
            self.interface.consume_outgoing().ack,
            4,
            "the ack must be reported every tick, since the client compares against it"
        )

    def test_win_is_sticky_within_a_tick(self) -> None:
        self.put(("is_win", 0), ("is_win", 1))
        self.assertEqual(self.interface.consume_outgoing().is_win, 1)

    def test_requests_and_data_are_passed_through(self) -> None:
        self.put(("req_cctx", True), ("req_li", True), ("data", (1, "level", 3)))
        package = self.interface.consume_outgoing()
        self.assertTrue(package.req_cctx)
        self.assertTrue(package.req_li)
        self.assertEqual(package.data, [(1, "level", 3)])

    def test_entries_without_a_value_are_skipped(self) -> None:
        self.put(("location", None), ("death_link", None))
        package = self.interface.consume_outgoing()
        self.assertIsNone(package.locations)
        self.assertIsNone(package.death_link)

    def test_the_queue_is_drained(self) -> None:
        self.put(("location", 1))
        self.interface.consume_outgoing()
        with self.assertRaises(queue.Empty):
            self.interface._get_queue.get_nowait()


class TestInterfaceAuthentication(unittest.TestCase):
    """The interface remembers which slot it was started for."""

    def setUp(self) -> None:
        self.interface = KhimeraDAMGCommunicationInterface()

    def test_unstarted_interface_authenticates_nothing(self) -> None:
        self.assertFalse(self.interface.authenticate("Tester", "12345"))

    def test_matching_credentials(self) -> None:
        self.interface.slot_name = "Tester"
        self.interface.seed = "12345"
        self.assertTrue(self.interface.authenticate("Tester", "12345"))

    def test_mismatched_credentials(self) -> None:
        self.interface.slot_name = "Tester"
        self.interface.seed = "12345"
        self.assertFalse(self.interface.authenticate("Someone else", "12345"))
        self.assertFalse(self.interface.authenticate("Tester", "54321"))
