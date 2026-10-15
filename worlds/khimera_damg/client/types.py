from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from NetUtils import NetworkItem  # type: ignore


@dataclass(frozen=True)
class ConnectionContext:
    ap_version: str
    host_world_version: str
    client_world_version: str
    slot_name: str
    seed: str
    last_ack: int
    options: dict[str, Any]
    generation_information: dict[str, Any]
    game_data: dict[str, Any]
    locations: set[int]
    item_list: list[tuple[int, NetworkItem]]
    has_goaled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ap_version":               self.ap_version,
            "host_world_version":       self.host_world_version,
            "client_world_version":     self.client_world_version,
            "slot_name":                self.slot_name,
            "seed":                     self.seed,
            "last_ack":                 self.last_ack,
            "options":                  self.options,
            "generation_information":   self.generation_information,
            "game_data":                self.game_data,
            "locations":                self.locations,
            "item_list":                self.item_list,
            "has_goaled":               self.has_goaled
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
    req_cctx: bool | None = None  # There really should be a better way to pass this information
    req_li: bool | None = None    # But this will do for now.

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_list":        self.item_list,
            "locations":        self.locations,
            "location_acks":    self.location_acks,
            "messages":         self.messages,
            "death_link":       self.death_link,
            "death_ack":        self.death_ack,
            "data":             self.data,
            "data_acks":        self.data_acks,
            "ack":              self.ack,
            "is_win":           self.is_win,
        }

    def merge_messages(self, merger: RuntimeInformation | None, merger_old: bool = False) -> RuntimeInformation:
        if merger is None:
            return self
        if merger_old:  # merger has older information
            if merger.messages is not None:
                self.messages = (
                    merger.messages +
                    [entry for entry in (self.messages or []) if entry not in merger.messages]
                )
        else:  # merger has newer information
            if merger.messages is not None:
                self.messages = (
                    [entry for entry in (self.messages or []) if entry not in merger.messages] +
                    merger.messages
                )
        return self
