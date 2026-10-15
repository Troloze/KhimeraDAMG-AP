# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Item table shape, pool composition, filler and trap rolls, and classification overrides."""

import unittest
from collections import Counter

from BaseClasses import ItemClassification, MultiWorld  # type: ignore
from test.general import setup_multiworld  # type: ignore

from ... import KhimeraDAMGWorld
from ...items import (
    books,
    default_filler,
    detonators,
    filler,
    filler_weights,
    gourmet_upgrades,
    item_frequencies,
    item_groups,
    item_table,
    make_item_id,
    stage_unlocks,
    traps,
    upgrades,
)
from ...types import ItemType, StageIndex, stage_entrances
from ..bases import ALL_SHUFFLES, BOOKS_WITHOUT_FAIRIES, NO_SHUFFLES, KhimeraTestBase

MAX_ID = 2 ** 53

# Option sets used by more than one assertion, named after the scenario they set up.
TRAP_HEAVY = {
    **NO_SHUFFLES,
    "trap_weight": 100,
    "balls_trap": "common"
}
TRAPS_DISABLED_AT_FULL_WEIGHT = {
    **NO_SHUFFLES,
    "trap_weight": 100
}
ALL_SHUFFLES_WITHOUT_TRAPS = {
    **ALL_SHUFFLES,
    "trap_weight": 0
}
FAIRIES_WITHOUT_BOOKS = {
    **NO_SHUFFLES,
    "shuffle_fairies": True
}


class TestItemTable(unittest.TestCase):
    """Checks on the static tables. No multiworld needed, so these stay cheap."""

    def test_ids_are_unique(self) -> None:
        seen: dict[int, str] = {}
        for name, data in item_table.items():
            clash = seen.get(data.item_id)
            self.assertIsNone(clash, f"item id {data.item_id} is used by both \"{clash}\" and \"{name}\"")
            seen[data.item_id] = name

    def test_ids_are_in_range(self) -> None:
        for name, data in item_table.items():
            self.assertGreater(data.item_id, 0, f"item \"{name}\" has id {data.item_id}, which must be > 0")
            self.assertLess(data.item_id, MAX_ID, f"item \"{name}\" has id {data.item_id}, which must be < 2**53")

    def test_names_are_not_numeric(self) -> None:
        # Archipelago rejects purely numeric item names, since they are ambiguous with ids.
        for name in item_table:
            self.assertFalse(name.isdigit(), f"item name \"{name}\" is purely numeric")
            self.assertEqual(name, name.strip(), f"item name \"{name}\" has leading or trailing whitespace")

    def test_id_layout_matches_item_type(self) -> None:
        # Every table is built with make_item_id(type, index); the id encodes the type, so the two
        # must agree. A copy-paste of the wrong ItemType is exactly what this catches.
        groups = {
            ItemType.SKILLS: upgrades,
            ItemType.STAGE_UNLOCK: stage_unlocks,
            ItemType.BOOK: books,
            ItemType.DETONATOR: detonators,
            ItemType.GOURMET_GAL: gourmet_upgrades,
            ItemType.FILLER: filler,
            ItemType.TRAPS: traps
        }
        for item_type, group in groups.items():
            for name, data in group.items():
                self.assertEqual(
                    data.item_id // 100000,
                    5000 + item_type.value,
                    f"item \"{name}\" sits in the {item_type.name} table but its id {data.item_id} "
                    f"encodes type {data.item_id // 100000 - 5000}"
                )

    def test_make_item_id_is_stable(self) -> None:
        self.assertEqual(make_item_id(ItemType.SKILLS, 1), 500000001)
        self.assertEqual(make_item_id(ItemType.TRAPS, 5), 500800005)

    def test_filler_weights_cover_every_filler(self) -> None:
        # items.validate_filler() asserts this at import time; this is the same check with a
        # message that names the difference.
        self.assertEqual(
            set(filler),
            set(filler_weights),
            f"filler and filler_weights disagree: only in filler {set(filler) - set(filler_weights)}, "
            f"only in filler_weights {set(filler_weights) - set(filler)}"
        )

    def test_default_filler_is_repeatable_filler(self) -> None:
        # get_filler_item_name returns this, and a unique item there breaks fill.
        self.assertIn(default_filler, filler, f"default filler \"{default_filler}\" is not in the filler table")
        self.assertEqual(item_table[default_filler].type, ItemClassification.filler)

    def test_item_groups_reference_real_items(self) -> None:
        for group_name, members in item_groups.items():
            for member in members:
                self.assertIn(member, item_table, f"item group \"{group_name}\" lists unknown item \"{member}\"")

    def test_every_stage_entrance_has_an_unlock_item(self) -> None:
        for stage, entrance_name in stage_entrances.items():
            self.assertIn(
                entrance_name,
                stage_unlocks,
                f"stage {StageIndex(stage).name} has entrance \"{entrance_name}\" but no unlock item"
            )

    def test_name_to_id_matches_table(self) -> None:
        expected = {name: data.item_id for name, data in item_table.items()}
        self.assertEqual(KhimeraDAMGWorld.item_name_to_id, expected)


class TestPoolDefaults(KhimeraTestBase):
    """Default options: no shuffles, so only unlocks, skills and filler."""

    options = NO_SHUFFLES

    def test_pool_matches_fillable_locations(self) -> None:
        pool = len(self.multiworld.itempool)
        locations = len(self.real_locations())
        self.assertEqual(
            pool,
            locations,
            f"item pool has {pool} items for {locations} fillable locations ({self.option_description()})"
        )

    def test_starting_unlocks_are_precollected(self) -> None:
        precollected = {item.name for item in self.multiworld.precollected_items[self.player]}
        expected = {stage_entrances[stage] for stage in self.world.starting_locations}
        self.assertEqual(
            precollected,
            expected,
            f"precollected items {sorted(precollected)} do not match the starting stages {sorted(expected)}"
        )

    def test_remaining_unlocks_are_in_the_pool(self) -> None:
        names = Counter(item.name for item in self.multiworld.itempool)
        for stage, entrance_name in stage_entrances.items():
            if stage in self.world.starting_locations:
                self.assertEqual(
                    names[entrance_name],
                    0,
                    f"\"{entrance_name}\" is a starting unlock but also appears in the pool"
                )
            else:
                self.assertEqual(
                    names[entrance_name],
                    1,
                    f"\"{entrance_name}\" appears {names[entrance_name]} times in the pool, expected exactly 1"
                )

    def test_all_skills_are_in_the_pool(self) -> None:
        names = Counter(item.name for item in self.multiworld.itempool)
        for skill in upgrades:
            self.assertEqual(names[skill], 1, f"skill \"{skill}\" appears {names[skill]} times, expected exactly 1")

    def test_unshuffled_categories_are_absent(self) -> None:
        names = {item.name for item in self.multiworld.itempool}
        for group in (books, detonators, gourmet_upgrades):
            overlap = names & set(group)
            self.assertEqual(overlap, set(), f"pool contains {sorted(overlap)} although the shuffle is off")
        self.assertNotIn("Fairy", names, "pool contains fairies although shuffle_fairies is off")

    def test_filler_fills_the_remainder(self) -> None:
        fixed = len(upgrades) + len(stage_unlocks) - len(self.world.starting_locations)
        expected_filler = len(self.real_locations()) - fixed
        rolled = [item for item in self.multiworld.itempool if item.name in filler or item.name in traps]
        self.assertEqual(
            len(rolled),
            expected_filler,
            f"{len(rolled)} filler/trap items were rolled, expected {expected_filler} "
            f"({len(self.real_locations())} locations - {fixed} fixed items)"
        )

    def test_no_traps_at_default_trap_weight(self) -> None:
        # trap_weight defaults to 0, and every trap defaults to disabled.
        rolled_traps = [item.name for item in self.multiworld.itempool if item.name in traps]
        self.assertEqual(rolled_traps, [], f"traps were rolled with the default trap options: {rolled_traps}")


class TestPoolAllShuffles(KhimeraTestBase):
    """Everything shuffled: the largest pool the world can produce."""

    options = ALL_SHUFFLES

    def test_pool_matches_fillable_locations(self) -> None:
        pool = len(self.multiworld.itempool)
        locations = len(self.real_locations())
        self.assertEqual(
            pool,
            locations,
            f"item pool has {pool} items for {locations} fillable locations ({self.option_description()})"
        )

    def test_shuffled_categories_are_complete(self) -> None:
        names = Counter(item.name for item in self.multiworld.itempool)
        for group_name, group in (("books", books), ("detonators", detonators), ("gourmet", gourmet_upgrades)):
            for entry in group:
                self.assertEqual(
                    names[entry],
                    1,
                    f"{group_name} entry \"{entry}\" appears {names[entry]} times in the pool, expected exactly 1"
                )

    def test_fairy_frequency(self) -> None:
        count = sum(1 for item in self.multiworld.itempool if item.name == "Fairy")
        self.assertEqual(
            count,
            item_frequencies["Fairy"],
            f"pool holds {count} fairies, item_frequencies asks for {item_frequencies['Fairy']}"
        )


class TestTrapRolls(KhimeraTestBase):
    """Every filler slot becomes a trap at weight 100 with a trap enabled."""

    options = TRAP_HEAVY

    def test_every_filler_slot_is_a_trap(self) -> None:
        rolled = [item.name for item in self.multiworld.itempool if item.name in filler or item.name in traps]
        plain_filler = [name for name in rolled if name in filler]
        self.assertEqual(
            plain_filler,
            [],
            f"trap_weight is 100 but {len(plain_filler)} plain filler items were rolled: {sorted(set(plain_filler))}"
        )
        self.assertGreater(len(rolled), 0, "no filler slots existed, so this test proves nothing")

    def test_only_enabled_traps_are_rolled(self) -> None:
        rolled = {item.name for item in self.multiworld.itempool if item.name in traps}
        self.assertEqual(
            rolled,
            {"Balls Trap"},
            f"only Balls Trap is enabled, but these traps were rolled: {sorted(rolled)}"
        )


class TestTrapsDisabled(KhimeraTestBase):
    """A high trap weight with every trap disabled must still produce no traps."""

    options = TRAPS_DISABLED_AT_FULL_WEIGHT

    def test_no_traps_are_rolled(self) -> None:
        rolled = {item.name for item in self.multiworld.itempool if item.name in traps}
        self.assertEqual(
            rolled,
            set(),
            f"trap_weight is 100 and every trap is disabled, but these traps were rolled: {sorted(rolled)}"
        )

    def test_filler_fills_every_slot(self) -> None:
        pool = len(self.multiworld.itempool)
        locations = len(self.real_locations())
        self.assertEqual(pool, locations, f"item pool has {pool} items for {locations} fillable locations")


class TestKiranDriveThruCoupling(KhimeraTestBase):
    """The Kiran Drive-Thru filler only exists while its trap counterpart is enabled."""

    options = ALL_SHUFFLES_WITHOUT_TRAPS

    def test_filler_is_absent_while_the_trap_is_disabled(self) -> None:
        # kiran_drive_by_trap defaults to disabled, so create_items drops the drive-thru from the
        # filler names it rolls from. This direction is deterministic; the reverse is a weighted
        # roll, so it is not asserted here.
        rolled = [item.name for item in self.multiworld.itempool if item.name == "Kiran Drive-Thru"]
        self.assertEqual(
            rolled,
            [],
            "Kiran Drive-Thru was rolled although the Kiran Drive-By trap is disabled"
        )


class TestClassificationOverrides(KhimeraTestBase):
    """``update_item_classification`` promotes two items, but only under the right options."""

    options = ALL_SHUFFLES

    def test_harpy_boost_is_progression_with_books(self) -> None:
        # One log book sits behind Harpy Boost, so the skill carries logic once books are shuffled.
        self.assertEqual(
            self.world.progression_overrides.get("Harpy Boost"),
            ItemClassification.progression,
            f"progression_overrides is {self.world.progression_overrides} with books and fairies shuffled"
        )
        item = self.get_item_by_name("Harpy Boost")
        self.assertTrue(item.advancement, "the Harpy Boost in the pool is not progression")

    def test_fairies_are_deprioritised(self) -> None:
        # The Fairy Queen book needs 12 fairies, so fairies carry logic, but 25 of them would
        # distort balancing if they were plain progression.
        self.assertEqual(
            self.world.progression_overrides.get("Fairy"),
            ItemClassification.progression_deprioritized_skip_balancing,
            f"progression_overrides is {self.world.progression_overrides} with books and fairies shuffled"
        )


class TestClassificationWithoutFairies(KhimeraTestBase):
    """Books shuffled, fairies not: the fairy promotion must not happen."""

    options = BOOKS_WITHOUT_FAIRIES

    def test_only_harpy_boost_is_promoted(self) -> None:
        self.assertEqual(
            self.world.progression_overrides,
            {"Harpy Boost": ItemClassification.progression},
            f"progression_overrides is {self.world.progression_overrides} ({self.option_description()})"
        )


class TestClassificationWithoutBooks(KhimeraTestBase):
    """No books: nothing is promoted at all."""

    options = FAIRIES_WITHOUT_BOOKS

    def test_nothing_is_promoted(self) -> None:
        self.assertEqual(
            self.world.progression_overrides,
            {},
            f"progression_overrides is {self.world.progression_overrides} ({self.option_description()})"
        )


class TestGroupWorldItemCreation(unittest.TestCase):
    """KR-001: an item link group world never runs ``generate_early``.

    ``MultiWorld.link_items`` calls ``create_item`` on the group world, which core builds through
    ``World.create_group``. Reading per-generation state in ``create_item`` crashed there, and
    core's own ``test_item_links`` failed with it, so this pins the contract: creating any item
    must work on a world that only ever had ``__init__`` called.
    """

    def setUp(self) -> None:
        self.multiworld: MultiWorld = setup_multiworld(KhimeraDAMGWorld, steps=())

    def test_group_world_creates_every_item(self) -> None:
        group = KhimeraDAMGWorld.create_group(self.multiworld, 2, {1})
        for name, data in item_table.items():
            with self.subTest(item=name):
                item = group.create_item(name)
                self.assertEqual(item.name, name)
                self.assertEqual(item.code, data.item_id)
                self.assertEqual(
                    item.classification,
                    data.type,
                    f"a group world created \"{name}\" as {item.classification!r}, expected its base "
                    f"classification {data.type!r}"
                )

    def test_group_world_has_no_progression_overrides(self) -> None:
        group = KhimeraDAMGWorld.create_group(self.multiworld, 2, {1})
        self.assertEqual(
            group.progression_overrides,
            {},
            "a group world must start with empty overrides; generate_early never runs for it"
        )
