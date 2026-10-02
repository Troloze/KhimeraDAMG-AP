from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from Options import Choice, DeathLink, OptionGroup, Range, StartInventoryPool, Toggle  # type: ignore
from worlds.AutoWorld import PerGameCommonOptions  # type: ignore

if TYPE_CHECKING:
    from . import KhimeraDAMGWorld


def create_option_groups() -> list[OptionGroup]:
    ret_group_list = []
    for name, options in khimera_option_groups.items():
        ret_group_list.append(OptionGroup(name=name, options=options))
    return ret_group_list


def adjust_option_values(world: "KhimeraDAMGWorld") -> None:
    pass


class VictoryCondition(Choice):
    """ The goal condition for the game.
    The Spider's Web: Defeat the pirate captain.

    Currently there is only one option, more will be implemented eventually."""
    display_name = "Victory Condition"
    option_the_spiders_web = 0
    default = 0


class ShuffleBooks(Toggle):
    """ Shuffles the log books into the item pool
    Only applies to books within the main game, having no effect to the halloween stage books."""
    display_name = "Shuffle Books"


class ShuffleDetonators(Toggle):
    """ If enabled, shuffles the detonators into the item pool. """
    display_name = "Shuffle Detonators"


class ShuffleFairies(Toggle):
    """ If enabled, shuffles the fairies into the item pool. """
    display_name = "Shuffle Fairies"


class ShuffleGourmetGal(Toggle):
    """ If enabled, shuffles the health upgrades into the item pool. """
    display_name = "Shuffle Gourmet Gal"


class TrapWeight(Range):
    """ From 0 to 100 percent, how likely it is for a filler item to be replaced with a trap

        If all traps are disabled, no traps will be set regardless of this setting.
    """
    display_name = "Trap Weight"
    range_start = 0
    range_end = 100
    default = 0


class BallsTrap(Choice):
    """ Settings for the "Balls" trap. """
    display_name = "Balls Trap"
    option_abundant = 0
    option_common = 1
    option_average = 2
    option_rare = 3
    option_very_rare = 4
    option_disabled = 5
    default = 5


class AviatorSwarmTrap(Choice):
    """ Settings for the "Floof Aviator Swarm" trap. """
    display_name = "Floof Aviator Swarm Trap"
    option_abundant = 0
    option_common = 1
    option_average = 2
    option_rare = 3
    option_very_rare = 4
    option_disabled = 5
    default = 5


class KiranDriveByTrap(Choice):
    """ Settings for the "Kiran Drive-By" trap. """
    display_name = "Kiran Drive-By Trap"
    option_abundant = 0
    option_common = 1
    option_average = 2
    option_rare = 3
    option_very_rare = 4
    option_disabled = 5
    default = 5


class BoxTrap(Choice):
    """ Settings for the "Box" trap. """
    display_name = "Box Trap"
    option_abundant = 0
    option_common = 1
    option_average = 2
    option_rare = 3
    option_very_rare = 4
    option_disabled = 5
    default = 5


class RandomEnemyTrap(Choice):
    """ Settings for the "Random Enemy" trap. """
    display_name = "Random Enemy Trap"
    option_abundant = 0
    option_common = 1
    option_average = 2
    option_rare = 3
    option_very_rare = 4
    option_disabled = 5
    default = 5


@dataclass
class KhimeraDAMGOptions(PerGameCommonOptions):
    death_link:                 DeathLink

    victory_condition:          VictoryCondition

    shuffle_books:              ShuffleBooks
    shuffle_detonators:         ShuffleDetonators
    shuffle_fairies:            ShuffleFairies
    shuffle_gourmet_gal:        ShuffleGourmetGal

    trap_weight:                TrapWeight

    balls_trap:                 BallsTrap
    floof_aviator_swarm_trap:   AviatorSwarmTrap
    kiran_drive_by_trap:        KiranDriveByTrap
    box_trap:                   BoxTrap
    random_enemy_trap:          RandomEnemyTrap

    start_inventory_from_pool:  StartInventoryPool


khimera_option_groups: dict[str, list[Any]] = {
    "General Options": [
        VictoryCondition, ShuffleBooks, ShuffleDetonators, ShuffleFairies, ShuffleGourmetGal
    ],
    "Trap Options": [
        TrapWeight, BallsTrap, AviatorSwarmTrap, KiranDriveByTrap, BoxTrap, RandomEnemyTrap
    ]
}


def make_trap_weights(world: "KhimeraDAMGWorld") -> dict[str, int]:
    def find_weight(val: int) -> int:
        return 2**(4 - val) if val != 5 else 0

    return {
        "Balls Trap":                   find_weight(world.options.balls_trap.value),
        "Floof Aviator Swarm Trap":     find_weight(world.options.floof_aviator_swarm_trap.value),
        "Kiran Drive-By Trap":          find_weight(world.options.kiran_drive_by_trap.value),
        "Box Trap":                     find_weight(world.options.box_trap.value),
        "Random Enemy Trap":            find_weight(world.options.random_enemy_trap.value)
    }
