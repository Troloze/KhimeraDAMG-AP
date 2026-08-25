from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from Options import DeathLink, OptionGroup, StartInventoryPool, Toggle
from worlds.AutoWorld import PerGameCommonOptions

if TYPE_CHECKING:
    from . import KhimeraDAMGWorld

def create_option_groups() -> list[OptionGroup]:
    ret_group_list = []
    for name, options in khimera_option_groups.items():
        ret_group_list.append(OptionGroup(name=name, options=options))
    return ret_group_list

def adjust_option_values(world: "KhimeraDAMGWorld"):
    pass

class ShuffleBooks(Toggle):
    """ If enabled, causes the books to be shuffled into the pool as items.
    Only applies to books within the main game, having no effect to the halloween stage books."""
    display_name = "ShuffleBooks"

class ShuffleDetonators(Toggle):
    """ If enabled, causes the secret detonators to be shuffled into the pool as items. """
    display_name = "ShuffleDetonators"

class ShuffleFairies(Toggle):
    """ If enabled, causes the fairies to be shuffled into the pool as items. """
    display_name = "ShuffleFairies"

class ShuffleGourmetGal(Toggle):
    """ If enabled, causes the health upgrades to be shuffled into the pool as items. """
    display_name = "ShuffleGourmetGal"


@dataclass
class KhimeraDAMGOptions(PerGameCommonOptions):
    death_link:                 DeathLink

    shuffle_books:              ShuffleBooks
    shuffle_detonators:         ShuffleDetonators
    shuffle_fairies:            ShuffleFairies
    shuffle_gourmet_gal:        ShuffleGourmetGal

    start_inventory_from_pool: StartInventoryPool

    pass


khimera_option_groups: dict[str, list[Any]] = {
    "General Options": [
        ShuffleBooks, ShuffleDetonators, ShuffleFairies, ShuffleGourmetGal
    ]
}
