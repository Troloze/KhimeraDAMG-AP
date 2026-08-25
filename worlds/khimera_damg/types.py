from enum import IntEnum
from typing import NamedTuple

from BaseClasses import Item, ItemClassification, Location
from rule_builder.rules import Rule


class KhimeraDAMGLocation(Location):
    game = "Khimera: Destroy All Monster Girls"

class KhimeraDAMGItem(Item):
    game = "Khimera: Destroy All Monster Girls"

class StageIndex(IntEnum):
    # Any/None/Some; Whatever doesn't fit in a single stage index goes here
    GENERAL = 0

    # Friendly stages
    RAGAZZA_TOWN = 1
    CHELSHIAS_HOUSE = 2
    FAIRIES_DOMAIN = 3
    QUIZ = 4

    # Main Stages
    RAGAZZA_PLAINS = 5
    MT_AFROKUPA = 6
    OIL_PLATFORM = 7
    SKY_FORTRESS = 8
    PUMPKIN_VALLEY = 9
    THE_BLACK_WIDOW = 10
    MECHANICAL_MAYHEM = 11
    THE_SPIDERS_WEB = 12

    # Extra Stages
    ICY_PATH = 13
    BRINE_CAVE = 14
    TOWER_OF_POWER = 15
    WINDY_WAY = 16

    # Harvest Event
    HARVEST_EVENT = 17

    # Cakeboy
    CAKEBOY = 18

class ItemType(IntEnum):
    SKILLS = 0
    STAGE_UNLOCK = 1
    FAIRY = 2
    BOOK = 3
    # CANDY = 4
    DETONATOR = 5
    GOURMET_GAL = 6
    # COSTUME = 7
    # TRAPS = 8
    FILLER = 9

class LocType(IntEnum):
    GENERAL = 0
    STAGE_CLEAR = 1
    FAIRY = 2
    BOOK = 3
    # CANDY = 4
    DETONATOR = 5
    GOURMET_GAL = 6

class LocData(NamedTuple):
    id: int
    stage: StageIndex
    rule: Rule | None

class ItemData(NamedTuple):
    id: int
    type: ItemClassification

stage_id_to_name:dict[StageIndex, str] = {
    StageIndex.GENERAL:             "General",
    StageIndex.RAGAZZA_TOWN:        "Ragazza Town",
    StageIndex.CHELSHIAS_HOUSE:     "Chelshia's House",
    StageIndex.FAIRIES_DOMAIN:      "The Fairies Domain",
    StageIndex.QUIZ:                "???",
    StageIndex.RAGAZZA_PLAINS:      "Ragazza Plains",
    StageIndex.MT_AFROKUPA:         "Mt. Afrokupa",
    StageIndex.OIL_PLATFORM:        "Oil Platform",
    StageIndex.SKY_FORTRESS:        "Sky Fortress",
    StageIndex.PUMPKIN_VALLEY:      "Pumpkin Valley",
    StageIndex.THE_BLACK_WIDOW:     "The Black Widow",
    StageIndex.MECHANICAL_MAYHEM:   "Mechanical Mayhem",
    StageIndex.THE_SPIDERS_WEB:     "The Spider's Web",
    StageIndex.ICY_PATH:            "Icy Path",
    StageIndex.BRINE_CAVE:          "Brine Cave",
    StageIndex.TOWER_OF_POWER:      "Tower of Power",
    StageIndex.WINDY_WAY:           "Windy Way",
    StageIndex.HARVEST_EVENT:       "Harvest Event",
    StageIndex.CAKEBOY:             "Cakeboy"
}

stage_entrances:dict[StageIndex, str] = {
    StageIndex.RAGAZZA_TOWN:        "Unlock Ragazza Town",
    StageIndex.CHELSHIAS_HOUSE:     "Unlock Chelshia's House",
    StageIndex.FAIRIES_DOMAIN:      "Unlock The Fairies Domain",
    StageIndex.QUIZ:                "Unlock ???",
    StageIndex.RAGAZZA_PLAINS:      "Unlock Ragazza Plains",
    StageIndex.MT_AFROKUPA:         "Unlock Mt. Afrokupa",
    StageIndex.OIL_PLATFORM:        "Unlock Oil Platform",
    StageIndex.SKY_FORTRESS:        "Unlock Sky Fortress",
    StageIndex.PUMPKIN_VALLEY:      "Unlock Pumpkin Valley",
    StageIndex.THE_BLACK_WIDOW:     "Unlock The Black Widow",
    StageIndex.MECHANICAL_MAYHEM:   "Unlock Mechanical Mayhem",
    StageIndex.THE_SPIDERS_WEB:     "Unlock The Spider's Web",
    StageIndex.ICY_PATH:            "Unlock Icy Path",
    StageIndex.BRINE_CAVE:          "Unlock Brine Cave",
    StageIndex.TOWER_OF_POWER:      "Unlock Tower of Power",
    StageIndex.WINDY_WAY:           "Unlock Windy Way"
}

loc_type_to_name:dict[LocType, str] = {
    LocType.GENERAL:                "General",
    LocType.STAGE_CLEAR:            "Clear",
    LocType.FAIRY:                  "Fairy",
    LocType.BOOK:                   "Log Book",
    LocType.DETONATOR:              "Detonator",
    LocType.GOURMET_GAL:            "Gourmet Gal"
}

stage_to_detonator_item_index: dict[StageIndex, str] = {
    StageIndex.ICY_PATH:        "MT Afrokupa Detonator",
    StageIndex.BRINE_CAVE:      "Oil Platform Detonator",
    StageIndex.TOWER_OF_POWER:  "Sky Fortress Detonator",
    StageIndex.WINDY_WAY:       "Pumpkin Valley Detonator"
}

extra_to_stage_index: dict[StageIndex, StageIndex] = {
    StageIndex.ICY_PATH:        StageIndex.MT_AFROKUPA,
    StageIndex.BRINE_CAVE:      StageIndex.OIL_PLATFORM,
    StageIndex.TOWER_OF_POWER:  StageIndex.SKY_FORTRESS,
    StageIndex.WINDY_WAY:       StageIndex.PUMPKIN_VALLEY
}
