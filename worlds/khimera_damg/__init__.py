from typing import ClassVar

from BaseClasses import Item, ItemClassification, MultiWorld, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, icon_paths
from worlds.LauncherComponents import launch as launch_component

from .generation_options import KhimeraDAMGOptions, create_option_groups
from .items import create_item, create_items, get_filler, item_groups, item_table
from .locations import loc_table
from .regions import create_regions
from .types import KhimeraDAMGItem, StageIndex


def client_launch(*args: str):
    from .client import launch
    launch_component(launch, name="KhimeraDAMGLauncher", args=args)
    pass

components.append(Component("Khimera: Destroy All Monster Girls Launcher", "KhimeraDAMGLauncher", func=client_launch,
                            component_type=Type.CLIENT, icon="khimera_damg"))
icon_paths["khimera_damg"] = f"ap:{__name__}/icons/chelshia.png"
starting_locations = [
    StageIndex.RAGAZZA_TOWN,
    StageIndex.CHELSHIAS_HOUSE,
    StageIndex.FAIRIES_DOMAIN,
    StageIndex.QUIZ,
    StageIndex.RAGAZZA_PLAINS]


class WebKhimeraDAMG(WebWorld):
    theme = "stone"
    option_groups = create_option_groups()

    def __init__(self):
        self.tutorials = [Tutorial(
                "Multiworld Setup Guide",
                "A guide for setting up Khimera: Destroy All Monster Girls to be played in Archipelago.",
                "English",
                "setup_en.md",
                "setup/en",
                ["Troloze"]
        )]

class KhimeraDAMGWorld(World):
    game = "Khimera: Destroy All Monster Girls"
    origin_region_name = "Map"
    item_name_to_id:ClassVar[dict[str, int]] = {name: data.id for name, data in item_table.items()}
    location_name_to_id:ClassVar[dict[str, int]] = {name: data.id for name, data in loc_table.items()}
    item_name_groups = item_groups
    options_dataclass = KhimeraDAMGOptions
    options: KhimeraDAMGOptions # type: ignore
    web = WebKhimeraDAMG()

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)


    def generate_early(self) -> None:
        self.starting_locations = starting_locations
        return super().generate_early()

    def create_regions(self) -> None:
        create_regions(self)

    def create_items(self) -> None:
        create_items(self)

    def create_event(self, event: str) -> KhimeraDAMGItem:
        return KhimeraDAMGItem(event, ItemClassification.progression, None, self.player)

    def set_rules(self) -> None:

        # Setting up the win condition.
        self.multiworld.get_location(
            "The Spider's Web: Clear",
            self.player
        ).place_locked_item(self.create_event("Victory"))

        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

        return super().set_rules()

    def create_item(self, name: str) -> Item:
        return create_item(self, name)

    def get_filler_item_name(self) -> str:
        return get_filler(self)



