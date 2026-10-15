# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The world class itself: slot data, the location information table, and the filler contract."""

import json

from BaseClasses import ItemClassification  # type: ignore
from Fill import distribute_items_restrictive  # type: ignore

from ... import APWORLD_VERSION, GAME_FULL_NAME, KhimeraDAMGWorld
from ...items import filler
from ..bases import ALL_SHUFFLES, NO_SHUFFLES, KhimeraTestBase

# The keys the client reads out of slot data. Adding one is fine; renaming or dropping one is a
# change the client has to be updated for at the same time.
EXPECTED_SLOT_DATA_KEYS = {
    "apworld_version",
    "options",
    "generation_information",
    "is_race",
    "location_information"
}

EXPECTED_SLOT_DATA_OPTIONS = {
    "death_link",
    "victory_condition",
    "shuffle_books",
    "shuffle_fairies",
    "shuffle_detonators",
    "shuffle_gourmet_gal"
}


class TestWorldClass(KhimeraTestBase):
    """Class-level attributes the client and core both depend on."""

    options = NO_SHUFFLES

    def test_game_name(self) -> None:
        self.assertEqual(KhimeraDAMGWorld.game, GAME_FULL_NAME)

    def test_required_client_version_is_a_version_tuple(self) -> None:
        version = KhimeraDAMGWorld.required_client_version
        self.assertEqual(len(version), 3, f"required_client_version is {version}, expected three numbers")
        for part in version:
            self.assertIsInstance(part, int, f"required_client_version is {version}, expected ints")

    def test_filler_item_name_is_repeatable(self) -> None:
        # get_filler_item_name is called as many times as fill needs, so it must never return a
        # unique item.
        name = self.world.get_filler_item_name()
        self.assertIn(name, filler, f"get_filler_item_name returned \"{name}\", which is not a filler item")
        self.assertEqual(
            self.world.create_item(name).classification,
            ItemClassification.filler,
            f"the filler item \"{name}\" is not classified as filler"
        )

    def test_create_item_rejects_unknown_names(self) -> None:
        with self.assertRaises(KeyError):
            self.world.create_item("Not An Item")


class TestSlotData(KhimeraTestBase):
    """Slot data is the only thing the client gets from generation, so its shape is a contract."""

    options = ALL_SHUFFLES

    def test_keys_are_unchanged(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual(
            set(slot_data),
            EXPECTED_SLOT_DATA_KEYS,
            f"slot data keys changed: added {sorted(set(slot_data) - EXPECTED_SLOT_DATA_KEYS)}, "
            f"removed {sorted(EXPECTED_SLOT_DATA_KEYS - set(slot_data))}"
        )

    def test_version_is_the_apworld_version(self) -> None:
        # The client maps this to a communication agent, so it has to be the world's own version.
        self.assertEqual(self.world.fill_slot_data()["apworld_version"], APWORLD_VERSION)

    def test_options_subset(self) -> None:
        options = self.world.fill_slot_data()["options"]
        self.assertEqual(
            set(options),
            EXPECTED_SLOT_DATA_OPTIONS,
            f"slot data options changed: added {sorted(set(options) - EXPECTED_SLOT_DATA_OPTIONS)}, "
            f"removed {sorted(EXPECTED_SLOT_DATA_OPTIONS - set(options))}"
        )
        self.assertEqual(
            options["shuffle_books"],
            1,
            f"shuffle_books is on, but slot data says {options['shuffle_books']}"
        )

    def test_slot_data_is_json_safe(self) -> None:
        # Slot data travels as JSON over the network, so every value has to survive a round trip.
        slot_data = self.world.fill_slot_data()
        try:
            json.dumps(slot_data)
        except TypeError as err:
            self.fail(f"slot data is not JSON serialisable: {err}")

    def test_location_information_after_fill(self) -> None:
        distribute_items_restrictive(self.multiworld)
        slot_data = self.world.fill_slot_data()
        info = slot_data["location_information"]
        expected_addresses = {loc.address for loc in self.real_locations()}
        self.assertEqual(
            set(info),
            expected_addresses,
            f"location information covers {len(info)} locations, the world has {len(expected_addresses)}"
        )
        for address, entry in info.items():
            self.assertEqual(
                len(entry),
                2,
                f"location {address} maps to {entry}, expected (classification, player)"
            )
            classification, player = entry
            self.assertIsInstance(classification, (int, ItemClassification))
            self.assertEqual(player, self.player, f"location {address} reports player {player}")

    def test_race_mode_hides_location_information(self) -> None:
        distribute_items_restrictive(self.multiworld)
        self.multiworld.is_race = True
        try:
            slot_data = self.world.fill_slot_data()
        finally:
            self.multiworld.is_race = False
        self.assertEqual(
            slot_data["location_information"],
            {},
            "race mode must not ship the per-location item information"
        )
        self.assertTrue(slot_data["is_race"], "is_race is not reported to the client")
