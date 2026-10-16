# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Location table shape, the id and naming conventions, and which locations each option creates."""

import unittest

from BaseClasses import CollectionState  # type: ignore

from ... import KhimeraDAMGWorld
from ...locations import (
    _make_data,
    _make_name,
    books,
    clears,
    detonators,
    fairies,
    gourmet_gal,
    loc_table,
    minibosses,
    upgrades,
)
from ...types import LocType, StageIndex, loc_type_to_name, stage_id_to_name
from ..bases import ALL_SHUFFLES, BOOKS_WITHOUT_FAIRIES, NO_SHUFFLES, KhimeraTestBase

MAX_ID = 2 ** 53

# Locations that carry a rule of their own, per locations.py. Kept here so that adding or
# removing one is a deliberate edit in two places rather than a silent change.
EXPECTED_RULE_LOCATIONS = {
    "Ragazza Town: Log Book - 1 (Scuttlebit)",
    "The Fairies Domain: Log Book - 2 (The Fairy Queen)"
}


class TestLocationTable(unittest.TestCase):
    """Checks on the static tables. No multiworld needed, so these stay cheap."""

    def test_ids_are_unique(self) -> None:
        seen: dict[int, str] = {}
        for name, data in loc_table.items():
            clash = seen.get(data.location_id)
            self.assertIsNone(clash, f"location id {data.location_id} is used by both \"{clash}\" and \"{name}\"")
            seen[data.location_id] = name

    def test_ids_are_in_range(self) -> None:
        for name, data in loc_table.items():
            self.assertGreater(
                data.location_id,
                0,
                f"location \"{name}\" has id {data.location_id}, which must be > 0"
            )
            self.assertLess(
                data.location_id,
                MAX_ID,
                f"location \"{name}\" has id {data.location_id}, which must be < 2**53"
            )

    def test_names_are_not_numeric(self) -> None:
        for name in loc_table:
            self.assertFalse(name.isdigit(), f"location name \"{name}\" is purely numeric")
            self.assertEqual(name, name.strip(), f"location name \"{name}\" has leading or trailing whitespace")

    def test_id_layout_matches_stage_and_type(self) -> None:
        # Per docs/Item and Location Conventions.md the id is stage * 10**7 + type * 10**5 + n,
        # so the id has to agree with the table the entry sits in and with its own stage field.
        groups = {
            LocType.STAGE_CLEAR: clears + upgrades,
            LocType.MINIBOSS: minibosses,
            LocType.FAIRY: fairies,
            LocType.BOOK: books,
            LocType.DETONATOR: detonators,
            LocType.GOURMET_GAL: gourmet_gal
        }
        for loc_type, group in groups.items():
            for name, data in group:
                stage_segment, rest = divmod(data.location_id, 10000000)
                type_segment, identifier = divmod(rest, 100000)
                self.assertEqual(
                    stage_segment,
                    data.stage.value,
                    f"location \"{name}\" is in stage {data.stage.name} but its id {data.location_id} "
                    f"encodes stage {stage_segment}"
                )
                self.assertEqual(
                    type_segment,
                    loc_type.value,
                    f"location \"{name}\" sits in the {loc_type.name} table but its id {data.location_id} "
                    f"encodes type {type_segment}"
                )
                self.assertNotEqual(identifier, 0, f"location \"{name}\" has identifier segment 0")

    def test_make_data_rejects_identifier_zero(self) -> None:
        # Identifier 0 would make the id collide with the stage/type prefix itself.
        with self.assertRaises(ValueError):
            _make_data(StageIndex.RAGAZZA_PLAINS, LocType.STAGE_CLEAR, 0)

    def test_make_name_follows_the_convention(self) -> None:
        self.assertEqual(
            _make_name(StageIndex.RAGAZZA_PLAINS, LocType.STAGE_CLEAR),
            f"{stage_id_to_name[StageIndex.RAGAZZA_PLAINS]}: {loc_type_to_name[LocType.STAGE_CLEAR]}"
        )
        self.assertEqual(
            _make_name(StageIndex.SKY_FORTRESS, LocType.MINIBOSS, "Versus Monday"),
            f"{stage_id_to_name[StageIndex.SKY_FORTRESS]}: {loc_type_to_name[LocType.MINIBOSS]} - Versus Monday"
        )
        # The Other stage is the one that gets no prefix.
        self.assertEqual(_make_name(StageIndex.OTHER, "Freeform"), "Freeform")

    def test_every_stage_is_known(self) -> None:
        for name, data in loc_table.items():
            self.assertIn(
                data.stage,
                stage_id_to_name,
                f"location \"{name}\" belongs to stage {data.stage}, which has no name"
            )

    def test_rules_are_where_they_are_expected(self) -> None:
        with_rules = {name for name, data in loc_table.items() if data.rule is not None}
        self.assertEqual(
            with_rules,
            EXPECTED_RULE_LOCATIONS,
            f"locations carrying rules changed: added {sorted(with_rules - EXPECTED_RULE_LOCATIONS)}, "
            f"removed {sorted(EXPECTED_RULE_LOCATIONS - with_rules)}"
        )

    def test_name_to_id_matches_table(self) -> None:
        expected = {name: data.location_id for name, data in loc_table.items()}
        self.assertEqual(KhimeraDAMGWorld.location_name_to_id, expected)

    def test_no_table_name_uses_the_event_prefix(self) -> None:
        # Events are named "Ev: ..." precisely so that they cannot shadow a real location name;
        # see KR-031. A table entry using the prefix would reintroduce the clash.
        clashes = [name for name in loc_table if name.startswith("Ev: ")]
        self.assertEqual(clashes, [], f"real locations use the event prefix: {clashes}")


class TestLocationsDefault(KhimeraTestBase):
    """Default options: clears, minibosses and skill locations only."""

    options = NO_SHUFFLES

    def test_only_mandatory_categories_exist(self) -> None:
        present = {loc.name for loc in self.real_locations()}
        expected = {name for name, _ in clears + minibosses + upgrades}
        self.assertEqual(
            present,
            expected,
            f"unexpected locations {sorted(present - expected)}, missing {sorted(expected - present)} "
            f"({self.option_description()})"
        )

    def test_optional_categories_are_absent(self) -> None:
        present = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for group_name, group in (("books", books), ("fairies", fairies), ("detonators", detonators)):
            overlap = present & {name for name, _ in group}
            self.assertEqual(
                overlap,
                set(),
                f"{group_name} locations exist although the shuffle is off: {sorted(overlap)}"
            )

    def test_addresses_match_the_table(self) -> None:
        for loc in self.real_locations():
            self.assertEqual(
                loc.address,
                loc_table[loc.name].location_id,
                f"location \"{loc.name}\" has address {loc.address}, the table says "
                f"{loc_table[loc.name].location_id}"
            )

    def test_victory_event_exists_and_is_the_goal(self) -> None:
        victory = self.multiworld.get_location("Ev: Victory", self.player)
        self.assertIsNone(victory.address, "the victory event must not carry an id")
        self.assertEqual(
            victory.parent_region.name,
            stage_id_to_name[StageIndex.THE_SPIDERS_WEB],
            f"the victory event sits in {victory.parent_region.name}"
        )
        # An empty state must not satisfy the goal, and a full one must. Collecting "everything
        # except the victory item" would prove nothing: CollectionState.collect sweeps for
        # advancements, which picks up reachable events on its own.
        condition = self.multiworld.completion_condition[self.player]
        self.assertFalse(
            condition(CollectionState(self.multiworld)),
            "the goal is satisfied by an empty state"
        )
        self.assertTrue(
            condition(self.multiworld.get_all_state()),
            "the goal is not satisfied even with every item collected"
        )


class TestLocationsAllShuffles(KhimeraTestBase):
    """Everything shuffled: every table entry has to exist exactly once."""

    options = ALL_SHUFFLES

    def test_every_table_entry_exists(self) -> None:
        present = {loc.name for loc in self.real_locations()}
        expected = set(loc_table)
        self.assertEqual(
            present,
            expected,
            f"unexpected locations {sorted(present - expected)}, missing {sorted(expected - present)}"
        )

    def test_only_the_victory_event_remains(self) -> None:
        events = {loc.name for loc in self.event_locations()}
        self.assertEqual(
            events,
            {"Ev: Victory"},
            f"with fairies shuffled the only event should be the goal, got {sorted(events)}"
        )


class TestFairyEvents(KhimeraTestBase):
    """Books shuffled, fairies not: the fairies become events so the Fairy Queen book stays in logic."""

    options = BOOKS_WITHOUT_FAIRIES

    def test_every_fairy_becomes_an_event(self) -> None:
        events = {loc.name for loc in self.event_locations()}
        expected = {f"Ev: {name}" for name, _ in fairies} | {"Ev: Victory"}
        self.assertEqual(
            events,
            expected,
            f"unexpected events {sorted(events - expected)}, missing {sorted(expected - events)}"
        )

    def test_event_names_never_shadow_real_locations(self) -> None:
        # KR-031: the events used to reuse the fairy location names, which have ids of their own,
        # and trackers then saw two different things under one name.
        for loc in self.event_locations():
            self.assertNotIn(
                loc.name,
                KhimeraDAMGWorld.location_name_to_id,
                f"event \"{loc.name}\" shares its name with a location that has an id"
            )

    def test_event_items_are_fairy_events(self) -> None:
        for loc in self.event_locations():
            if loc.name == "Ev: Victory":
                continue
            self.assertIsNotNone(loc.item, f"event \"{loc.name}\" holds no item")
            self.assertEqual(
                loc.item.name,
                "Ev: Fairy",
                f"event \"{loc.name}\" holds \"{loc.item.name}\", expected the fairy event item"
            )
            self.assertNotIn(
                loc.item.name,
                KhimeraDAMGWorld.item_name_to_id,
                f"event item \"{loc.item.name}\" shares its name with a real item"
            )
