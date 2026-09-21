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
    SKY_FORTRESS = 6
    MT_AFROKUPA = 7
    PUMPKIN_VALLEY = 8
    OIL_PLATFORM = 9
    THE_BLACK_WIDOW = 10
    MECHANICAL_MAYHEM = 11
    THE_SPIDERS_WEB = 12

    # Extra Stages
    TOWER_OF_POWER = 13
    ICY_PATH = 14
    WINDY_WAY = 15
    BRINE_CAVE = 16

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

# ==================
# =     Client     =
# ==================


@dataclass(frozen=True)
class ConnectionContext:
    ap_version: str
    host_world_version: str
    client_world_version: str
    slot_name: str
    seed: str
    last_ack: int
    options: dict[str, Any]
    generation_info: dict[str, Any]
    game_data: dict[str, Any]
    locations: set[int]
    item_list: list[tuple[int, NetworkItem]]
    has_goaled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ap_version":           self.ap_version,
            "host_world_version":   self.host_world_version,
            "client_world_version": self.client_world_version,
            "slot_name":            self.slot_name,
            "seed":                 self.seed,
            "last_ack":             self.last_ack,
            "options":              self.options,
            "generation_info":      self.generation_info,
            "game_data":            self.game_data,
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
    data: list[tuple[int, str, Any]] | None = None
    data_acks: list[int] | None = None
    death_link: tuple[str, int, str] | None = None
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
            "data":             self.data,
            "data_acks":         self.data_acks,
            "ack":              self.ack,
            "is_win":           self.is_win
        }

    def merge(self, merger: RuntimeInformation | None, merger_old: bool = False) -> RuntimeInformation:
        if merger is None:
            return self
        if merger.locations is not None:
            self.locations = (self.locations or set()) | merger.locations
        if merger.location_acks is not None:
            self.location_acks = (self.location_acks or set()) | merger.location_acks
        self.is_win = bool(self.is_win or merger.is_win)
        if merger_old:  # merger has older information
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
            # if self is not None, maintain
            if self.death_link is None:
                self.death_link = merger.death_link
            if merger.item_list is not None:
                self.item_list = (
                    merger.item_list +
                    [entry for entry in (self.item_list or []) if entry not in merger.item_list]
                )
            if merger.data_acks is not None:
                self.data_acks = (
                    merger.data_acks +
                    [entry for entry in (self.data_acks or []) if entry not in merger.data_acks]
                )
            if merger.messages is not None:
                self.messages = (
                    merger.messages +
                    [entry for entry in (self.messages or []) if entry not in merger.messages]
                )
            if self.data is None:
                # Only allow new information, whatever is lost will be re-sent.
                self.data = merger.data
                pass
        else:  # merger has newer information
            # if merger is not None, overwrite
            if merger.ack is not None:
                self.ack = merger.ack
            # if merger is not None, overwrite
            if (
                merger.death_ack is not None and
                not merger.death_ack == -1
            ):
                self.death_ack = merger.death_ack
            # if merger is not None, overwrite
            if merger.death_link is not None:
                self.death_link = merger.death_link
            if merger.item_list is not None:
                self.item_list = (
                    [entry for entry in (self.item_list or []) if entry not in merger.item_list] +
                    merger.item_list
                )

            if merger.data_acks is not None:
                self.data_acks = (
                    [entry for entry in (self.data_acks or []) if entry not in merger.data_acks] +
                    merger.data_acks
                )
            if merger.messages is not None:
                self.messages = (
                    [entry for entry in (self.messages or []) if entry not in merger.messages] +
                    merger.messages
                )
            if merger.data is not None:
                # Only allow new information, whatever is lost will be re-sent.
                self.data = merger.data
        return self
