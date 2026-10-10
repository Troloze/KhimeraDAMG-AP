from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple

from BaseClasses import Item, ItemClassification, Location  # type: ignore
from rule_builder.rules import Rule  # type: ignore


class KhimeraDAMGLocation(Location):
    game = "Khimera: Destroy All Monster Girls"


class KhimeraDAMGItem(Item):
    game = "Khimera: Destroy All Monster Girls"


class StageIndex(IntEnum):
    """ Matches the internal IDS used by the game, do NOT change the indexes. """
    # Friendly stages
    RAGAZZA_TOWN = 9
    FAIRIES_DOMAIN = 13
    CHELSHIAS_HOUSE = 14
    QUIZ = 16

    # Main Stages
    RAGAZZA_PLAINS = 0
    SKY_FORTRESS = 1
    MT_AFROKUPA = 2
    PUMPKIN_VALLEY = 3
    OIL_PLATFORM = 4

    # Extra Stages
    TOWER_OF_POWER = 5
    ICY_PATH = 6
    WINDY_WAY = 7
    BRINE_CAVE = 8

    # Final Stages
    THE_BLACK_WIDOW = 10
    MECHANICAL_MAYHEM = 11
    THE_SPIDERS_WEB = 12

    # Harvest Event
    HARVEST_EVENT = 17

    # CREDITS = 15  # No locations will ever be sent here, even the game never writes state changes to id 15

    # Not tracked by the internal ids
    CAKEBOY = 18
    OTHER = 19


class ItemType(IntEnum):
    SKILLS = 0
    STAGE_UNLOCK = 1
    FAIRY = 2
    BOOK = 3
    # CANDY = 4
    DETONATOR = 5
    GOURMET_GAL = 6
    # COSTUME = 7
    TRAPS = 8
    FILLER = 9


class LocType(IntEnum):
    GENERAL = 0
    STAGE_CLEAR = 1
    FAIRY = 2
    BOOK = 3
    # CANDY = 4
    DETONATOR = 5
    GOURMET_GAL = 6
    MINIBOSS = 7


class LocData(NamedTuple):
    location_id: int
    stage: StageIndex
    rule: Rule | None


class ItemData(NamedTuple):
    item_id: int
    type: ItemClassification


stage_id_to_name: dict[StageIndex, str] = {
    StageIndex.OTHER:               "Other",
    StageIndex.RAGAZZA_TOWN:        "Ragazza Town",
    StageIndex.CHELSHIAS_HOUSE:     "Chelshia's House",
    StageIndex.FAIRIES_DOMAIN:      "The Fairies Domain",
    StageIndex.QUIZ:                "???",
    StageIndex.RAGAZZA_PLAINS:      "Ragazza Plains",
    StageIndex.SKY_FORTRESS:        "Sky Fortress",
    StageIndex.MT_AFROKUPA:         "Mt. Afrokupa",
    StageIndex.PUMPKIN_VALLEY:      "Pumpkin Valley",
    StageIndex.OIL_PLATFORM:        "Oil Platform",
    StageIndex.THE_BLACK_WIDOW:     "The Black Widow",
    StageIndex.MECHANICAL_MAYHEM:   "Mechanical Mayhem",
    StageIndex.THE_SPIDERS_WEB:     "The Spider's Web",
    StageIndex.TOWER_OF_POWER:      "Tower of Power",
    StageIndex.ICY_PATH:            "Icy Path",
    StageIndex.WINDY_WAY:           "Windy Way",
    StageIndex.BRINE_CAVE:          "Brine Cave",
    StageIndex.HARVEST_EVENT:       "Harvest Event",
    StageIndex.CAKEBOY:             "Cakeboy"
}

stage_entrances: dict[StageIndex, str] = {
    StageIndex.RAGAZZA_TOWN:        "Unlock Ragazza Town",
    StageIndex.CHELSHIAS_HOUSE:     "Unlock Chelshia's House",
    StageIndex.FAIRIES_DOMAIN:      "Unlock The Fairies Domain",
    StageIndex.QUIZ:                "Unlock ???",
    StageIndex.RAGAZZA_PLAINS:      "Unlock Ragazza Plains",
    StageIndex.SKY_FORTRESS:        "Unlock Sky Fortress",
    StageIndex.PUMPKIN_VALLEY:      "Unlock Pumpkin Valley",
    StageIndex.MT_AFROKUPA:         "Unlock Mt. Afrokupa",
    StageIndex.OIL_PLATFORM:        "Unlock Oil Platform",
    StageIndex.THE_BLACK_WIDOW:     "Unlock The Black Widow",
    StageIndex.MECHANICAL_MAYHEM:   "Unlock Mechanical Mayhem",
    StageIndex.THE_SPIDERS_WEB:     "Unlock The Spider's Web",
    StageIndex.TOWER_OF_POWER:      "Unlock Tower of Power",
    StageIndex.ICY_PATH:            "Unlock Icy Path",
    StageIndex.WINDY_WAY:           "Unlock Windy Way",
    StageIndex.BRINE_CAVE:          "Unlock Brine Cave"
}

loc_type_to_name: dict[LocType, str] = {
    LocType.GENERAL:                "General",
    LocType.STAGE_CLEAR:            "Clear",
    LocType.MINIBOSS:               "Miniboss",
    LocType.FAIRY:                  "Fairy",
    LocType.BOOK:                   "Log Book",
    LocType.DETONATOR:              "Detonator",
    LocType.GOURMET_GAL:            "Gourmet Gal"
}

stage_to_detonator_item_index: dict[StageIndex, str] = {
    StageIndex.TOWER_OF_POWER:  "Sky Fortress Detonator",
    StageIndex.ICY_PATH:        "MT Afrokupa Detonator",
    StageIndex.WINDY_WAY:       "Pumpkin Valley Detonator",
    StageIndex.BRINE_CAVE:      "Oil Platform Detonator"

}

extra_to_stage_index: dict[StageIndex, StageIndex] = {
    StageIndex.TOWER_OF_POWER:  StageIndex.SKY_FORTRESS,
    StageIndex.ICY_PATH:        StageIndex.MT_AFROKUPA,
    StageIndex.WINDY_WAY:       StageIndex.PUMPKIN_VALLEY,
    StageIndex.BRINE_CAVE:      StageIndex.OIL_PLATFORM
}
