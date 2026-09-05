from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, NamedTuple

from BaseClasses import Item, ItemClassification, Location  # type: ignore
from NetUtils import NetworkItem  # type: ignore
from rule_builder.rules import Rule  # type: ignore

# ==================
# =   Generation   =
# ==================


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
    TRAPS = 8
    FILLER = 9


class LocType(IntEnum):
    GENERAL = 0
    STAGE_CLEAR = 1
    MINIBOSS = 2
    FAIRY = 3
    BOOK = 4
    # CANDY = 5
    DETONATOR = 6
    GOURMET_GAL = 7


class LocData(NamedTuple):
    location_id: int
    stage: StageIndex
    rule: Rule | None


class ItemData(NamedTuple):
    item_id: int
    type: ItemClassification


stage_id_to_name: dict[StageIndex, str] = {
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

stage_entrances: dict[StageIndex, str] = {
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

# ==================
# =     Client     =
# ==================


@dataclass(frozen=True)
class ConnectionContext:
    ap_version: str
    host_world_version: str
    client_world_version: str
    slot_name: str
    last_ack: int
    options: dict[str, Any]
    slot_data: dict[str, Any]
    locations: set[int]
    item_list: list[tuple[int, NetworkItem]]
    has_goaled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ap_version":           self.ap_version,
            "host_world_version":   self.host_world_version,
            "client_world_version": self.client_world_version,
            "slot_name":            self.slot_name,
            "last_ack":             self.last_ack,
            "options":              self.options,
            "slot_data":            self.slot_data,
            "locations":            self.locations,
            "item_list":            self.item_list,
            "has_goaled":           self.has_goaled
        }


@dataclass(frozen=True)
class LocationInformation:
    enabled: bool
    loc_info: dict[int, tuple[int, int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled":  self.enabled,
            "loc_info": self.loc_info
        }


@dataclass
class RuntimeInformation:
    item_list: list[tuple[int, NetworkItem]] | None = None
    locations: set[int] | None = None
    location_acks: set[int] | None = None
    messages: list[tuple[int, str]] | None = None
    death_link: list[tuple[int, int, str]] | None = None
    death_ack: int | None = None
    ack: int | None = None
    is_win: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_list":        self.item_list,
            "locations":        self.locations,
            "location_acks":    self.location_acks,
            "messages":         self.messages,
            "death_link":       self.death_link,
            "death_ack":        self.death_ack,
            "ack":              self.ack,
            "is_win":           self.is_win
        }

    def merge(self, merger: RuntimeInformation | None, merger_first: bool = False) -> RuntimeInformation:
        if merger is None:
            return self
        if merger.locations is not None:
            self.locations = (self.locations or set()) | merger.locations
        if merger.location_acks is not None:
            self.location_acks = (self.location_acks or set()) | merger.location_acks
        self.is_win = bool(self.is_win or merger.is_win)
        if not merger_first:
            # if merger is not None, overwrite
            if merger.ack is not None:
                self.ack = merger.ack
            # if merger is not None, overwrite
            if (
                merger.death_ack is not None and
                not merger.death_ack == -1
            ):
                self.death_ack = merger.death_ack
            if merger.item_list is not None:
                self.item_list = (self.item_list or []) + merger.item_list
            if merger.messages is not None:
                self.messages = (self.messages or []) + merger.messages
            if merger.death_link is not None:
                self.death_link = (self.death_link or []) + merger.death_link
        else:
            # if self is not None, maintain
            if self.ack is None:
                self.ack = merger.ack
            # if self is not None, maintain
            if (
                self.death_ack is None and
                merger.death_ack is not None and
                not merger.death_ack == -1
            ):
                self.death_ack = merger.death_ack
            if merger.item_list is not None:
                self.item_list = merger.item_list + (self.item_list or [])
            if merger.messages is not None:
                self.messages = merger.messages + (self.messages or [])
            if merger.death_link is not None:
                self.death_link = merger.death_link + (self.death_link or [])
        return self
