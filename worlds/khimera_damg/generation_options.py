from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from Options import Choice, DeathLink, OptionGroup, StartInventoryPool, Toggle  # type: ignore
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


@dataclass
class KhimeraDAMGOptions(PerGameCommonOptions):
    death_link:                 DeathLink

    victory_condition:          VictoryCondition

    shuffle_books:              ShuffleBooks
    shuffle_detonators:         ShuffleDetonators
    shuffle_fairies:            ShuffleFairies
    shuffle_gourmet_gal:        ShuffleGourmetGal

    start_inventory_from_pool: StartInventoryPool


khimera_option_groups: dict[str, list[Any]] = {
    "General Options": [
        VictoryCondition, ShuffleBooks, ShuffleDetonators, ShuffleFairies, ShuffleGourmetGal
    ]
}
