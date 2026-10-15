# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Option behaviour: the full shuffle matrix, the trap weight curve, and the YAML key surface."""

import unittest
from typing import Any, ClassVar

from BaseClasses import MultiWorld  # type: ignore
from test.general import setup_multiworld  # type: ignore
from test.param import classvar_matrix  # type: ignore

from ... import KhimeraDAMGWorld
from ...generation_options import (
    KhimeraDAMGOptions,
    create_option_groups,
    khimera_option_groups,
    make_trap_weights,
)
from ...items import traps
from ..bases import SHUFFLE_KEYS, KhimeraTestBase, describe_options

# Location, item pool and event counts for every combination of the four shuffles, keyed by
# (books, fairies, detonators, gourmet). Measured against this world; the point of the table is
# that an accidental edit to a location or item table shows up as a number change here.
EXPECTED_COUNTS: dict[tuple[bool, ...], tuple[int, int]] = {
    (False, False, False, False): (33, 1),
    (False, False, False, True): (37, 1),
    (False, False, True, False): (37, 1),
    (False, False, True, True): (41, 1),
    (False, True, False, False): (58, 1),
    (False, True, False, True): (62, 1),
    (False, True, True, False): (62, 1),
    (False, True, True, True): (66, 1),
    (True, False, False, False): (71, 26),
    (True, False, False, True): (75, 26),
    (True, False, True, False): (75, 26),
    (True, False, True, True): (79, 26),
    (True, True, False, False): (96, 1),
    (True, True, False, True): (100, 1),
    (True, True, True, False): (100, 1),
    (True, True, True, True): (104, 1)
}

# The option fields are the player-facing YAML keys, so they are a released API: renaming one
# breaks every existing player file. Changing this set has to be deliberate.
EXPECTED_OPTION_KEYS = {
    "death_link",
    "victory_condition",
    "shuffle_books",
    "shuffle_detonators",
    "shuffle_fairies",
    "shuffle_gourmet_gal",
    "trap_weight",
    "balls_trap",
    "floof_aviator_swarm_trap",
    "kiran_drive_by_trap",
    "box_trap",
    "random_enemy_trap",
    "start_inventory_from_pool"
}

TRAP_OPTION_KEYS = [
    "balls_trap",
    "floof_aviator_swarm_trap",
    "kiran_drive_by_trap",
    "box_trap",
    "random_enemy_trap"
]


def make_world(**options: Any) -> KhimeraDAMGWorld:
    """A world with the given options and no generation steps run."""
    multiworld: MultiWorld = setup_multiworld(KhimeraDAMGWorld, steps=(), options=options)
    return multiworld.worlds[1]


@classvar_matrix(
    shuffle_books=[False, True],
    shuffle_fairies=[False, True],
    shuffle_detonators=[False, True],
    shuffle_gourmet_gal=[False, True]
)
class TestShuffleMatrix(KhimeraTestBase):
    """Every combination of the four shuffles, including Archipelago's own default tests.

    ``classvar_matrix`` unrolls this into one test class per combination, so a failure names the
    combination that produced it instead of hiding inside a loop.
    """

    shuffle_books: ClassVar[bool]
    shuffle_fairies: ClassVar[bool]
    shuffle_detonators: ClassVar[bool]
    shuffle_gourmet_gal: ClassVar[bool]

    def setUp(self) -> None:
        self.options = {
            "shuffle_books": self.shuffle_books,
            "shuffle_fairies": self.shuffle_fairies,
            "shuffle_detonators": self.shuffle_detonators,
            "shuffle_gourmet_gal": self.shuffle_gourmet_gal
        }
        super().setUp()

    def combination(self) -> tuple[bool, ...]:
        return tuple(bool(self.options[key]) for key in SHUFFLE_KEYS)

    def test_pool_matches_fillable_locations(self) -> None:
        pool = len(self.multiworld.itempool)
        locations = len(self.real_locations())
        self.assertEqual(
            pool,
            locations,
            f"item pool has {pool} items for {locations} fillable locations ({self.option_description()})"
        )

    def test_counts_are_unchanged(self) -> None:
        expected = EXPECTED_COUNTS[self.combination()]
        actual = (len(self.real_locations()), len(self.event_locations()))
        self.assertEqual(
            actual,
            expected,
            f"got {actual[0]} locations and {actual[1]} events, expected {expected[0]} and {expected[1]} "
            f"({self.option_description()}). If this change was intended, update EXPECTED_COUNTS."
        )


class TestTrapWeights(unittest.TestCase):
    """``make_trap_weights`` turns each trap's rarity choice into a relative weight."""

    def test_weight_curve(self) -> None:
        # abundant (0) through very_rare (4) halve each step; disabled (5) means weight 0.
        expected = {0: 16, 1: 8, 2: 4, 3: 2, 4: 1, 5: 0}
        for value, weight in expected.items():
            world = make_world(balls_trap=value)
            weights = make_trap_weights(world)
            self.assertEqual(
                weights["Balls Trap"],
                weight,
                f"balls_trap={value} produced weight {weights['Balls Trap']}, expected {weight}"
            )

    def test_every_trap_has_a_weight(self) -> None:
        world = make_world()
        weights = make_trap_weights(world)
        self.assertEqual(
            set(weights),
            set(traps),
            f"make_trap_weights covers {sorted(weights)}, the trap table holds {sorted(traps)}"
        )

    def test_all_disabled_by_default(self) -> None:
        world = make_world()
        weights = make_trap_weights(world)
        self.assertEqual(
            sum(weights.values()),
            0,
            f"traps default to disabled, but the weights are {weights}"
        )

    def test_each_option_drives_its_own_trap(self) -> None:
        for key in TRAP_OPTION_KEYS:
            world = make_world(**{key: 0})
            weights = make_trap_weights(world)
            enabled = {name for name, weight in weights.items() if weight > 0}
            self.assertEqual(
                len(enabled),
                1,
                f"setting {key}=abundant enabled {sorted(enabled)}, expected exactly one trap"
            )


class TestOptionSurface(unittest.TestCase):
    """The option dataclass itself: keys, groups and defaults."""

    def test_option_keys_are_unchanged(self) -> None:
        declared = set(KhimeraDAMGOptions.__annotations__)
        self.assertEqual(
            declared,
            EXPECTED_OPTION_KEYS,
            f"option keys changed: added {sorted(declared - EXPECTED_OPTION_KEYS)}, "
            f"removed {sorted(EXPECTED_OPTION_KEYS - declared)}. These are player-facing YAML keys."
        )

    def test_world_uses_the_dataclass(self) -> None:
        self.assertIs(KhimeraDAMGWorld.options_dataclass, KhimeraDAMGOptions)

    def test_grouped_options_belong_to_the_dataclass(self) -> None:
        by_type = {option: key for key, option in KhimeraDAMGOptions.type_hints.items()}
        for group_name, options in khimera_option_groups.items():
            for option in options:
                self.assertIn(
                    option,
                    by_type,
                    f"option group \"{group_name}\" lists {option.__name__}, which is not an option of this world"
                )

    def test_option_groups_are_built_from_the_table(self) -> None:
        groups = create_option_groups()
        self.assertEqual(
            [group.name for group in groups],
            list(khimera_option_groups),
            "create_option_groups does not mirror khimera_option_groups"
        )
        for group in groups:
            self.assertEqual(group.options, khimera_option_groups[group.name])

    def test_every_option_has_a_display_name(self) -> None:
        for key, option in KhimeraDAMGOptions.type_hints.items():
            if key not in EXPECTED_OPTION_KEYS:
                continue  # Inherited from PerGameCommonOptions; core names those.
            self.assertTrue(
                getattr(option, "display_name", ""),
                f"option \"{key}\" has no display_name, so the WebHost would show its class name"
            )

    def test_defaults_describe_a_vanilla_run(self) -> None:
        world = make_world()
        defaults = {key: getattr(world.options, key).value for key in SHUFFLE_KEYS}
        self.assertEqual(
            defaults,
            dict.fromkeys(SHUFFLE_KEYS, 0),
            f"the shuffles no longer default to off: {describe_options(defaults)}"
        )
        self.assertEqual(world.options.trap_weight.value, 0, "trap_weight no longer defaults to 0")
