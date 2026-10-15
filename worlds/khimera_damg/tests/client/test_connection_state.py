# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Session state: death links, acks, and the documents built from them.

Three report findings live in here:

* KR-006 - the persisted item ack lagged one step, so filler and traps fired again after a
  relaunch. Covered by ``TestItemAckPersistence``.
* KR-007 - game death ids restart at 1 on every launch, so the acked-id set has to be reset
  with the game rather than kept for the whole slot session. Covered by ``TestDeathLinks``.
* KR-011 - a context requested while the server is away used to be built from cleared state.
  Covered by ``TestConnectionContextBuilder``.
"""

from __future__ import annotations

import asyncio
import unittest
from contextlib import suppress
from typing import Any

from CommonClient import ClientStatus  # type: ignore

from ... import APWORLD_VERSION
from ...client.client import KhimeraDAMGConnectionState, KhimeraDAMGContext, get_game_id
from ...client.storage import KhimeraDAMGStorageHandler as Storage
from ...client.types import RuntimeInformation
from ..support.fakes import FakeContext, make_connection_context, make_item
from ..support.sandbox import AsyncRedirectedTestCase, RedirectedTestCase

SLOT_NAME = "Tester"
SEED = "12345678901234567890"
# The real id for this slot and seed, so that storage lookups line up however the client
# derives the id it uses.
GAME_ID = get_game_id(SLOT_NAME, SEED)


class TestDeathLinks(unittest.TestCase):
    """Death links in both directions, and the ack bookkeeping that stops duplicates."""

    def setUp(self) -> None:
        self.context = FakeContext()
        self.state = KhimeraDAMGConnectionState(self.context)

    def test_a_game_death_is_held_until_acked(self) -> None:
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.assertEqual(self.state.get_game_deathlink(), ("Tester", 1, "died"))
        self.state.set_game_deathlink_ack(1)
        self.assertIsNone(self.state.get_game_deathlink(), "the death link survived its own ack")

    def test_an_already_acked_death_is_only_re_acked(self) -> None:
        # The game resends until it sees the ack, so a repeat must not reach the server twice.
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.state.set_game_deathlink_ack(1)
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.assertIsNone(self.state.get_game_deathlink(), "a resent death link was sent to the server again")
        self.assertEqual(self.state.get_game_deathlink_ack(), 1, "the resent death link was not re-acked")

    def test_pending_acks_are_drained_once(self) -> None:
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.state.set_game_deathlink_ack(1)
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.assertEqual(self.state.get_game_deathlink_ack(), 1)
        self.assertIsNone(self.state.get_game_deathlink_ack(), "the pending ack was reported twice")

    def test_host_deaths_get_increasing_ids(self) -> None:
        self.state.set_host_deathlink("Someone", "was slain")
        first = self.state.get_host_deathlink()
        self.state.set_host_deathlink_ack(first[1])
        self.state.set_host_deathlink("Someone else", "was slain")
        second = self.state.get_host_deathlink()
        self.assertEqual(first[1], 1)
        self.assertEqual(second[1], 2, "host death ids must keep counting up within a session")

    def test_host_death_ack_only_clears_the_matching_id(self) -> None:
        self.state.set_host_deathlink("Someone", "was slain")
        self.state.set_host_deathlink_ack(99)
        self.assertIsNotNone(
            self.state.get_host_deathlink(),
            "an ack for a different id cleared the pending death link"
        )

    def test_reset_clears_the_acked_ids(self) -> None:
        # KR-007: the game numbers its deaths from 1 on every launch. Without this reset, the
        # first deaths of a relaunched game look like ones that were already handled.
        self.state.set_game_deathlink(("Tester", 1, "died"))
        self.state.set_game_deathlink_ack(1)
        self.state.reset()
        self.state.set_game_deathlink(("Tester", 1, "died after a relaunch"))
        self.assertEqual(
            self.state.get_game_deathlink(),
            ("Tester", 1, "died after a relaunch"),
            "death id 1 from a relaunched game was dropped as a duplicate"
        )

    def test_reset_clears_everything_else_too(self) -> None:
        self.state.set_host_deathlink("Someone", "was slain")
        self.state.set_location_acked({1, 2})
        self.state.set_item_ack(5)
        self.state.set_req_cctx()
        self.state.set_req_li()
        self.state.reset()
        self.assertIsNone(self.state.get_host_deathlink())
        self.assertEqual(self.state.locations_acked, set())
        self.assertEqual(self.state.get_last_ack(), 0)
        self.assertIsNone(self.state.get_req_cctx())
        self.assertIsNone(self.state.get_req_li())


class TestLocationAndItemAcks(unittest.TestCase):
    """What still needs sending to the game, given what it has acked."""

    def setUp(self) -> None:
        self.context = FakeContext()
        self.state = KhimeraDAMGConnectionState(self.context)

    def test_unacked_locations(self) -> None:
        self.context.checked_locations = {1, 2, 3}
        self.state.set_location_acked(2)
        self.assertEqual(self.state.get_unacked_locations(), {1, 3})

    def test_unacked_locations_accepts_a_set(self) -> None:
        self.context.checked_locations = {1, 2, 3}
        self.state.set_location_acked({1, 2})
        self.assertEqual(self.state.get_unacked_locations(), {3})

    def test_item_acks_only_move_forward(self) -> None:
        # The game's ack is the highest index it has applied; a lower value is stale information.
        self.state.set_item_ack(5)
        self.state.set_item_ack(2)
        self.assertEqual(
            self.state.get_last_ack(),
            5,
            "a stale ack moved the counter backwards, which would resend items the game already has"
        )

    def test_unacked_items_are_indexed_from_one(self) -> None:
        self.context.items_received = [make_item(111), make_item(222), make_item(333)]
        self.state.set_item_ack(1)
        self.assertEqual(
            self.state.get_unacked_items(),
            [(2, make_item(222)), (3, make_item(333))],
            "the game indexes received items from 1, and acks by that index"
        )

    def test_nothing_is_unacked_once_everything_is_acked(self) -> None:
        self.context.items_received = [make_item(111)]
        self.state.set_item_ack(1)
        self.assertEqual(self.state.get_unacked_items(), [])


class TestDataStorage(RedirectedTestCase):
    """Game data arriving from the game is written through to the save file."""

    def setUp(self) -> None:
        super().setUp()
        self.context = FakeContext(game_id=GAME_ID)
        self.state = KhimeraDAMGConnectionState(self.context)

    def test_data_is_stored_and_acked(self) -> None:
        self.state.set_data([(1, "level", 3), (2, "coins", 50)])
        self.assertEqual(Storage.get("level", GAME_ID, None, "game_data", folder="game_data"), 3)
        self.assertEqual(Storage.get("coins", GAME_ID, None, "game_data", folder="game_data"), 50)
        self.assertEqual(sorted(self.state.get_pending_data_ack()), [1, 2])

    def test_pending_acks_are_drained_once(self) -> None:
        self.state.set_data([(1, "level", 3)])
        self.assertEqual(self.state.get_pending_data_ack(), [1])
        self.assertIsNone(
            self.state.get_pending_data_ack(),
            "data acks were reported twice, so the game would see them again next tick"
        )

    def test_nothing_is_stored_without_a_game(self) -> None:
        self.state.context = FakeContext(game_id=None)
        self.state.set_data([(1, "level", 3)])
        self.assertIsNone(
            self.state.get_pending_data_ack(),
            "data was acked although there is no save file to write it to"
        )


class ContextTestCase(AsyncRedirectedTestCase):
    """Builds a real client context with both runtime folders redirected.

    ``CommonContext.__init__`` creates its keep-alive task immediately, so this only works
    inside a running loop; the task is cancelled again in cleanup.
    """

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.ctx = KhimeraDAMGContext(None, None)
        self.addAsyncCleanup(self.close_context)
        self.ctx.game_id = GAME_ID
        self.ctx.slot_name = SLOT_NAME
        self.ctx.host_seed = SEED
        self.ctx.host_world_version = APWORLD_VERSION
        self.ctx.team = 0
        self.ctx.slot = 1
        self.ctx.slot_data = {
            "apworld_version": APWORLD_VERSION,
            "options": {"death_link": 0},
            "generation_information": {},
            "is_race": False,
            "location_information": {}
        }

    async def close_context(self) -> None:
        self.ctx.exit_event.set()
        self.ctx.keep_alive_task.cancel()
        with suppress(asyncio.CancelledError):
            await self.ctx.keep_alive_task

    async def process(self, **fields: Any) -> None:
        await self.ctx._process_game_package(RuntimeInformation(**fields))

    def stored_ack(self) -> int:
        return Storage.get("last_ack", GAME_ID, 0, folder="game_data")


class TestItemAckPersistence(ContextTestCase):
    """KR-006: the ack written to disk is the one the game reported, not the previous one."""

    async def test_the_reported_ack_is_persisted(self) -> None:
        await self.process(ack=5)
        self.assertEqual(
            self.stored_ack(),
            5,
            "the stored ack lags behind the game, so every item in the gap is applied again after "
            "a relaunch"
        )
        self.assertEqual(self.ctx.connection_state.get_last_ack(), 5)

    async def test_persistence_follows_each_increase(self) -> None:
        for ack in (1, 4, 9):
            await self.process(ack=ack)
            self.assertEqual(self.stored_ack(), ack, f"the stored ack is not {ack} after the game reported it")

    async def test_a_stale_ack_does_not_rewind_storage(self) -> None:
        await self.process(ack=5)
        await self.process(ack=2)
        self.assertEqual(self.stored_ack(), 5, "a stale ack rewound the stored value")

    async def test_nothing_is_stored_without_a_game_id(self) -> None:
        self.ctx.game_id = None
        await self.process(ack=5)
        self.assertEqual(
            self.ctx.connection_state.get_last_ack(),
            5,
            "the in-memory ack should still move while no save file is known"
        )
        self.assertEqual(self.stored_ack(), 0)


class TestGamePackageHandling(ContextTestCase):
    """The rest of ``_process_game_package``."""

    async def test_locations_are_recorded(self) -> None:
        self.ctx.server_locations = {1, 2}
        await self.process(locations={1, 3})
        self.assertEqual(
            self.ctx.locations_checked,
            {1},
            "only locations the server knows about may be recorded as checked"
        )

    async def test_a_win_is_reported_once(self) -> None:
        await self.process(is_win=True)
        self.assertTrue(self.ctx.finished_game)
        await self.process(is_win=True)
        self.assertTrue(self.ctx.finished_game)

    async def test_a_missing_win_flag_does_nothing(self) -> None:
        await self.process(is_win=False)
        self.assertFalse(self.ctx.finished_game)

    async def test_no_package_is_a_no_op(self) -> None:
        await self.ctx._process_game_package(None)
        self.assertEqual(self.stored_ack(), 0)

    async def test_a_context_request_builds_one(self) -> None:
        await self.process(req_cctx=True)
        self.assertIsNotNone(self.ctx.cctx, "the requested context was not built")
        self.assertTrue(self.ctx.connection_state.get_req_cctx(), "the request was not flagged for the agent")

    async def test_a_location_information_request_is_flagged(self) -> None:
        await self.process(req_li=True)
        self.assertTrue(self.ctx.connection_state.get_req_li())


class TestConnectionContextBuilder(ContextTestCase):
    """``_make_cctx``: what the game is told when it asks to resume."""

    async def test_items_are_indexed_from_one(self) -> None:
        self.ctx.items_received = [make_item(111), make_item(222)]
        cctx = self.ctx._make_cctx()
        self.assertEqual([index for index, _item in cctx.item_list], [1, 2])

    async def test_the_larger_ack_wins(self) -> None:
        # The in-memory value can be ahead of the file, and the file can be ahead after a
        # client restart; sending the smaller one would replay items.
        Storage.store("last_ack", 5, GAME_ID, folder="game_data")
        self.ctx.connection_state.set_item_ack(2)
        self.assertEqual(self.ctx._make_cctx().last_ack, 5, "the stored ack was ignored")

        self.ctx.connection_state.set_item_ack(9)
        self.assertEqual(self.ctx._make_cctx().last_ack, 9, "the in-memory ack was ignored")

    async def test_game_data_is_read_from_storage(self) -> None:
        Storage.store("level", 3, GAME_ID, "game_data", folder="game_data")
        self.assertEqual(self.ctx._make_cctx().game_data, {"level": 3})

    async def test_versions_and_identity(self) -> None:
        cctx = self.ctx._make_cctx()
        self.assertEqual(cctx.client_world_version, APWORLD_VERSION)
        self.assertEqual(cctx.host_world_version, APWORLD_VERSION)
        self.assertEqual(cctx.slot_name, SLOT_NAME)
        self.assertEqual(cctx.seed, SEED)
        self.assertEqual(
            cctx.game_id,
            GAME_ID,
            "the context has to remember which save file it belongs to; that is what makes it "
            "reusable after the slot fields are cleared"
        )

    async def test_goal_state_comes_from_the_server(self) -> None:
        self.assertFalse(self.ctx._make_cctx().has_goaled)
        self.ctx.stored_data[f"_read_client_status_{self.ctx.team}_{self.ctx.slot}"] = ClientStatus.CLIENT_GOAL
        self.assertTrue(self.ctx._make_cctx().has_goaled, "a goaled slot must be told so when it resumes")

    async def test_a_disconnected_client_reuses_the_last_context(self) -> None:
        # KR-011: the slot fields are cleared on disconnect, and the game may still ask for a
        # context while the client reconnects. The cached context stands in for the cleared
        # fields, but the save data has to be re-read, since the game kept playing.
        previous = make_connection_context(slot_name=SLOT_NAME, seed=SEED)
        self.ctx.cctx = previous
        self.ctx.slot_name = None
        self.ctx.game_id = None
        self.ctx.connection_state.set_item_ack(3)
        Storage.store("level", 7, GAME_ID, "game_data", folder="game_data")

        cctx = self.ctx._make_cctx()
        self.assertEqual(cctx.slot_name, previous.slot_name, "the reused context lost its slot name")
        self.assertEqual(cctx.seed, previous.seed)
        self.assertEqual(cctx.game_id, previous.game_id, "the reused context lost its save file id")
        self.assertEqual(
            cctx.game_data,
            {"level": 7},
            "the reused context must carry the save data as it stands now, not as it was on disconnect"
        )
        self.assertEqual(cctx.last_ack, 3, "the reused context lost the ack held in memory")

    async def test_a_disconnected_client_without_history_refuses(self) -> None:
        self.ctx.cctx = None
        self.ctx.slot_name = None
        with self.assertRaises(RuntimeError):
            self.ctx._make_cctx()


class TestLocationInformationBuilder(ContextTestCase):
    """``_make_li``: the per-location item table, as it arrives in slot data."""

    async def test_keys_from_slot_data_are_coerced_to_int(self) -> None:
        # Slot data travels as JSON, so the integer keys come back as strings.
        self.ctx.slot_data["location_information"] = {"100": [1, 2]}
        li = self.ctx._make_li()
        self.assertEqual(li.loc_info, {100: (1, 2)}, f"location information was built as {li.loc_info}")

    async def test_race_mode_disables_the_table(self) -> None:
        self.ctx.slot_data["is_race"] = True
        self.assertFalse(self.ctx._make_li().enabled, "race mode must disable the location information")

    async def test_missing_table_is_empty(self) -> None:
        self.ctx.slot_data["location_information"] = None
        li = self.ctx._make_li()
        self.assertEqual(li.loc_info, {})
        self.assertTrue(li.enabled)
