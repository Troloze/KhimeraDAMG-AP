from collections.abc import Mapping
from typing import Any, ClassVar

from BaseClasses import Item, ItemClassification, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, icon_paths
from worlds.LauncherComponents import launch as launch_component

from .generation_options import KhimeraDAMGOptions, create_option_groups
from .items import create_item, create_items, get_filler, item_groups, item_table, update_item_classification
from .locations import apply_location_rules, loc_table
from .regions import create_regions
from .types import StageIndex

APWORLD_VERSION = "0.0.2"

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
    required_client_version = (0, 6, 7)
    item_name_to_id:ClassVar[dict[str, int]] = {name: data.id for name, data in item_table.items()}
    location_name_to_id:ClassVar[dict[str, int]] = {name: data.id for name, data in loc_table.items()}
    item_name_groups = item_groups
    options_dataclass = KhimeraDAMGOptions
    options: KhimeraDAMGOptions # type: ignore
    web = WebKhimeraDAMG()


    def generate_early(self) -> None:
        self.starting_locations = starting_locations
        self.progression_overrides:dict[str, ItemClassification] = {}
        update_item_classification(self)
        return super().generate_early()

    def create_regions(self) -> None:
        create_regions(self)

    def create_items(self) -> None:
        create_items(self)

    def set_rules(self) -> None:

        apply_location_rules(self)

        # Setting up the win condition.
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

        return super().set_rules()

    def fill_slot_data(self) -> Mapping[str, Any]:
        return {
            "apworld_version": APWORLD_VERSION,
            "options": self.options.as_dict(
                "death_link",
                "shuffle_books",
                "shuffle_fairies",
                "shuffle_detonators",
                "shuffle_gourmet_gal"
            )
        }

    def create_item(self, name: str) -> Item:
        return create_item(self, name)

    def get_filler_item_name(self) -> str:
        return get_filler(self)



