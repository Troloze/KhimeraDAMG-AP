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
