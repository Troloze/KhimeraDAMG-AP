from __future__ import annotations

import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar

from NetUtils import NetworkItem  # type: ignore
from platformdirs import user_data_dir

from ...misc import normalize_and_sanitize
from ..classes import CommunicationContract

logger = logging.getLogger("Client")

unknown_entry_type_set: set[tuple[str, ...]] = set()


def validate_int_non_negative(value: int) -> None:
    if value < 0:
        raise ValueError("Attempted to set a negative value to a non negative field.")


def validate_bool(value: int) -> None:
    if value not in [0, 1]:
        raise ValueError("Attempted to set an invalid value to a boolean field that takes only 0 or 1.")


def validate_list(value: list) -> None:
    if len(value) <= 1:
        return
    list_type = type(value[0])
    for i in range(len(value)):
        if not isinstance(value[i], list_type):
            raise TypeError("List contains mixed types.")


def validate_version(version: str) -> None:
    values: list[str] = version.split(".")
    error = ValueError(
        'Version has to contain only 3 non negative integers separated by dots. (i.e., "X.Y.Z")'
    )

    if version.count(".") != 2:
        raise error
    if len(values) != 3:
        raise error
    for entry in values:
        try:
            val = int(entry)
        except ValueError as err:
            raise error from err
        if val < 0:
            raise error


def normalize_number(value: int | float) -> int | float:
    return int(value) if (isinstance(value, float) and value.is_integer()) else value


class OptionDataHandler:
    option_type_map: ClassVar[dict[str, str]] = {
        "death_link":               "NV",
        "victory_condition":        "NV",
        "shuffle_books":            "NV",
        "shuffle_fairies":          "NV",
        "shuffle_detonators":       "NV",
        "shuffle_gourmet_gal":      "NV",
    }

    @classmethod
    def format_option(cls, options: dict[str, Any]) -> dict[str, Any]:
        names = []
        types = []
        values = []
        count: int = 0
        for entry, value in options.items():
            e_type = cls.option_type_map.get(entry)
            # This shouldn't ever be necessary.
            clean_entry = normalize_and_sanitize(entry)
            if e_type == "NV":
                names.append(clean_entry)
                types.append(e_type)
                values.append(value)
            elif e_type == "SV":
                names.append(clean_entry)
                types.append(e_type)
                clean_value = normalize_and_sanitize(value)
                values.append(clean_value)
            elif e_type == "NL":
                validate_list(value)
                names.append(clean_entry)
                types.append(e_type)
                values.append(value)
            elif e_type == "SL":
                validate_list(value)
                names.append(clean_entry)
                types.append(e_type)
                values.append([
                    normalize_and_sanitize(v) for v in value
                ])
            elif e_type == "D":
                names.append(clean_entry)
                types.append(e_type)
                new_d = {}
                for e, v in value.items():
                    e_ = normalize_and_sanitize(e)
                    if isinstance(v, int):
                        new_d[e_] = v
                    elif isinstance(v, str):
                        new_d[e_] = normalize_and_sanitize(v)
                    else:
                        s = (entry, e, type(v).__name__)
                        if s not in unknown_entry_type_set:
                            unknown_entry_type_set.add(s)
                            logger.warning(
                                "Unknown dict value type was ignored: "
                                f"dict: {entry}, entry: {e}, type: {type(v)}"
                            )
                        continue
                values.append(new_d)
            else:
                s = (entry,)
                if s not in unknown_entry_type_set:
                    unknown_entry_type_set.add(s)
                    logger.warning(f"Unknown entry was ignored: {entry} - {value}")
                continue
            count += 1

        return {
            "names": names,
            "types": types,
            "values": values,
            "count": count
        }

    @classmethod
    def format_data(cls, data: dict[str, Any]) -> dict[str, Any]:
        names = []
        types = []
        values = []
        count: int = 0
        for entry, value in data.items():
            e_type = type(value).__name__
            if e_type == "str":
                e_type = "SV"
            elif e_type == "int" or e_type == "float":
                e_type = "NV"
            elif e_type == "list":
                if len(value) > 0:
                    e_type = type(value[0]).__name__
                    if e_type == "str":
                        e_type = "SL"
                    elif e_type == "int" or e_type == "float":
                        e_type = "NL"
                    else:
                        e_type = f"UNKNOWN ({e_type})"
                else:
                    e_type = "NL"
            elif e_type == "dict":
                e_type = "D"
            else:
                e_type = f"UNKNOWN ({e_type})"
            # This shouldn't ever be necessary.
            clean_entry = normalize_and_sanitize(entry)
            if e_type == "NV":
                names.append(clean_entry)
                types.append(e_type)
                clean_value = normalize_number(value)
                values.append(clean_value)
            elif e_type == "SV":
                names.append(clean_entry)
                types.append(e_type)
                clean_value = normalize_and_sanitize(value)
                values.append(clean_value)
            elif e_type == "NL":
                # validate_list(value)  # Data is controled by the game, we can skip validation
                names.append(clean_entry)
                types.append(e_type)
                values.append(
                    [normalize_number(v) for v in value]
                )
            elif e_type == "SL":
                # validate_list(value)  # Data is controled by the game, we can skip validation
                names.append(clean_entry)
                types.append(e_type)
                values.append([
                    normalize_and_sanitize(v) for v in value
                ])
            elif e_type == "D":
                names.append(clean_entry)
                types.append(e_type)
                new_d = {}
                for e, v in value.items():
                    e_ = normalize_and_sanitize(e)
                    if isinstance(v, int):
                        new_d[e_] = normalize_number(v)
                    elif isinstance(v, str):
                        new_d[e_] = normalize_and_sanitize(v)
                    else:
                        s = (entry, e, type(v).__name__)
                        if s not in unknown_entry_type_set:
                            unknown_entry_type_set.add(s)
                            logger.warning(
                                "Unknown dict value type was ignored: "
                                f"dict: {entry}, entry: {e}, type: {type(v)}"
                            )
                        continue
                values.append(new_d)
            else:
                s = (entry,)
                if s not in unknown_entry_type_set:
                    unknown_entry_type_set.add(s)
                    logger.warning(f"Unknown entry was ignored. ({entry}: {e_type} = {value})")
                continue
            count += 1

        return {
            "names": names,
            "types": types,
            "values": values,
            "count": count
        }

    @classmethod
    def read_data(cls, data: dict[str, Any]) -> list[tuple[int, str, Any]]:
        data_list: list[tuple[int, str, Any]] = []
        names: list[str] = data["names"]
        types: list[str] = data["types"]
        ids: list[float] = data["ids"]
        values: list[Any] = data["values"]
        count: int = int(data["count"])
        if not (len(names) == len(types) and len(types) == len(ids) and len(ids) == len(values)):
            logger.warning("Malformed data received from game")
            return []
        for i in range(count):
            c_name, c_type, c_id, c_value = names[i], types[i], int(ids[i]), values[i]
            if c_type == "SV":
                if not isinstance(c_value, str):
                    logger.warning(f"Game passed a string type with a non-string object ({c_name})")
                    # Let's warn and store it anyway for now.
                    # continue
            elif c_type == "NV":
                if not isinstance(c_value, (int, float)):
                    logger.warning(f"Game passed a number type with a non-number object ({c_name})")
                    # Let's warn and store it anyway for now.
                    # continue
            elif c_type == "SL" or c_type == "NL":
                if not isinstance(c_value, list):
                    logger.warning(f"Game passed a list type with a non-list object ({c_name})")
                    # Let's warn and store it anyway for now.
                    # continue
            elif c_type == "D":
                if not isinstance(c_value, dict):
                    logger.warning(f"Game passed a dict type with a non-dict object ({c_name})")
                    # Let's warn and store it anyway for now.
                    # continue
            elif c_type == "RM":
                c_value = None
            else:
                logger.warning(f"Game has attempted to store an unknown type ({c_name}, {c_type})")
            data_list.append((c_id, c_name, c_value))
        return data_list


class ContractV1(CommunicationContract):
    type_to_writer: ClassVar[dict[str, str]] = {
        "cctx":     "_write_context",
        "li":       "_write_location_information",
        "hi":       "_write_host_info",
        "cshb":     "_write_state_flag",
        "csc":      "_write_state_flag"
    }

    type_to_reader: ClassVar[dict[str, str]] = {
        "gi":       "_read_game_info",
        "gsreq":    "_read_state_flag",
        "gshb":     "_read_state_flag",
        "gsack":    "_read_state_flag",
        "gswin":    "_read_state_flag"
    }

    @classmethod
    def write_content(cls, content_type: str, params: dict[str, Any]) -> tuple[str, int]:

        writer = cls.type_to_writer.get(content_type)
        if writer is None:
            raise ValueError(f"Attempt to create unknown type of content: {content_type}")
        return getattr(cls, writer)(params)

    @classmethod
    def read_content(cls, content_type: str, content: str) -> dict[str, Any]:

        reader = cls.type_to_reader.get(content_type)
        if reader is None:
            raise ValueError(f"Attempt to read unknown type of content: {content_type}")
        return getattr(cls, reader)(content)

    @classmethod
    def parse_events(cls, events: dict[str, Any]) -> tuple[str, int]:
        return (json.dumps({"message": events}), 0)

    @classmethod
    def parse_message(cls, msg: str) -> tuple[dict[str, Any], int]:
        return (json.loads(msg), 0)

    @classmethod
    def get_sandbox_folder(cls) -> Path:
        return Path(user_data_dir("khimera_ap", False))

    @classmethod
    def _write_context(cls, params: dict[str, Any]) -> tuple[str, int]:
        ap_version: str = params["ap_version"]
        host_world_version: str = params["host_world_version"]
        client_world_version: str = params["client_world_version"]
        slot_name: str = params["slot_name"]
        seed: str = params["seed"]
        last_ack: int = params["last_ack"]
        options: dict[str, Any] = params["options"]
        slot_data: dict[str, Any] = params["slot_data"]
        game_data: dict[str, Any] = params["game_data"]
        locations: set[int] = params["locations"]
        item_list: list[tuple[int, NetworkItem]] = params["item_list"]
        has_goaled: bool = params["has_goaled"]

        validate_version(ap_version)
        validate_version(host_world_version)
        validate_version(client_world_version)
        if not last_ack == -1:
            validate_int_non_negative(last_ack)
        validate_bool(has_goaled)

        ap_version = normalize_and_sanitize(ap_version)
        host_world_version = normalize_and_sanitize(host_world_version)
        client_world_version = normalize_and_sanitize(client_world_version)
        slot_name = normalize_and_sanitize(slot_name)
        seed = normalize_and_sanitize(seed)

        options_ = OptionDataHandler.format_option(options)
        slot_data_ = OptionDataHandler.format_data(slot_data)
        game_data_ = OptionDataHandler.format_data(game_data)

        item_ids_ = [-1]
        player_ids_ = [-1]
        count_ = 0
        for _, item in sorted(item_list, key=lambda entry: entry[0]):
            item_ids_.append(item.item)
            player_ids_.append(item.player)
            count_ += 1
        item_list_ = {
            "item_ids": item_ids_,
            "player_ids": player_ids_,
            "count": count_
        }

        meta = {
                "archipelago_version": ap_version,
                "host_world_version": host_world_version,
                "client_world_version": client_world_version,
                "slot_name": slot_name,
                "seed": seed
        }

        session = {}
        if count_ > 0:
            session["item_list"] = item_list_
        if len(locations) > 0:
            session["location_ids"] = list(locations)
        if last_ack > 0:
            session["last_ack"] = last_ack
        if has_goaled:
            session["is_win"] = 1

        message: dict[str, Any] = {
            "meta": meta,
            "options": options_,
            "slot_data": slot_data_,
            "game_data": game_data_,
            "session": session
        }

        return cls.parse_events(message)

    @classmethod
    def _write_location_information(cls, params: dict[str, Any]) -> tuple[str, int]:
        enabled: bool = params["enabled"]
        if not enabled:
            return cls.parse_events({
                "enabled": 0,
                "locations": {
                    "location_ids": [],
                    "location_classifications": [],
                    "player_ids": [],
                    "count": 0
                }
            })

        loc_info: dict[int, tuple[int, int]] | None = params["loc_info"]

        location_ids_ = []
        location_classifications_ = []
        player_ids_ = []
        count_ = 0
        if loc_info is not None:
            for location, (classification, player) in loc_info.items():
                try:
                    validate_int_non_negative(int(location))
                    validate_int_non_negative(int(classification))
                    validate_int_non_negative(int(player))
                except ValueError as err:
                    raise ValueError(
                        f"Location id ({location}),"
                        f"classification ({classification}) and"
                        f"player id ({player})"

                        "all have to be non negative values."
                    ) from err
                except TypeError as err:
                    raise ValueError(
                        f"Location id ({location}),"
                        f"classification ({classification}) and"
                        f"player id ({player})"

                        "all have to be non negative values."
                    ) from err

                location_ids_.append(int(location))
                location_classifications_.append(int(classification))
                player_ids_.append(int(player))
                count_ += 1

        message: dict[str, Any] = {
            "enabled": 1,
            "locations": {
                "location_ids": location_ids_,
                "location_classifications": location_classifications_,
                "player_ids": player_ids_,
                "count": count_
            }
        }

        return cls.parse_events(message)

    @classmethod
    def _write_host_info(cls, params: dict[str, Any]) -> tuple[str, int]:
        messages: list[tuple[int, str]] | None = params["messages"]
        item_list: list[tuple[int, NetworkItem]] | None = params["item_list"]
        death_link: tuple[str, int, str] | None = params["death_link"]
        location_ids: set[int] | None = params["locations"]
        death_ack: int | None = params["death_ack"]
        data_acks: list[int] | None = params["data_acks"]

        message: dict[str, Any] = {}

        if messages is not None:
            senders_ = []
            messages__ = []
            count_ = 0
            for (sender, msg) in messages:
                senders_.append(sender)
                messages__.append(normalize_and_sanitize(msg))
                count_ += 1
            messages_: dict[str, Any] = {
                "senders": senders_,
                "messages": messages__,
                "count": count_
            }
            message["messages"] = messages_

        if death_link is not None:
            death_links_: dict[str, Any] = {
                "sender": normalize_and_sanitize(death_link[0]),
                "death_id": death_link[1],
                "message": normalize_and_sanitize(death_link[2]),
            }
            message["death_link"] = death_links_

        if item_list is not None:
            item_ids_ = []
            player_ids_ = []
            item_indexes_ = []
            item_count_ = 0
            for index, item in item_list:
                item_ids_.append(item.item)
                player_ids_.append(item.player)
                item_indexes_.append(index)
                item_count_ += 1
            item_list_: dict[str, Any] = {
                "item_ids": item_ids_,
                "player_ids": player_ids_,
                "item_indexes": item_indexes_,
                "count": item_count_
            }
            message["item_list"] = item_list_

        if location_ids is not None:
            location_ids_ = list(location_ids)
            message["location_ids"] = location_ids_

        if death_ack is not None:
            message["death_ack"] = death_ack

        if data_acks is not None:
            message["data_acks"] = list(data_acks)

        return cls.parse_events(message)

    @classmethod
    def _write_state_flag(cls, params: dict[str, Any]) -> tuple[str, int]:
        flag = params["flag"]
        value = params["value"]
        flag = f"{value}.{flag}"
        return normalize_and_sanitize(flag), 0

    @classmethod
    def _read_game_info(cls, msg: str) -> dict[str, Any]:
        message = None
        exit_code = 1

        class GetOutOfHereError(Exception):
            pass
        with suppress(json.JSONDecodeError, GetOutOfHereError):
            parsed = cls.parse_message(msg)
            decoded = parsed[0]
            if not isinstance(decoded, dict):
                raise GetOutOfHereError
            message = decoded.get("message")
            if not isinstance(message, dict):
                message = None
                raise GetOutOfHereError
            exit_code = parsed[1]
        # read data
        if message is not None:
            data = message.get("data")
            if data is not None:
                try:
                    parsed_data = OptionDataHandler.read_data(data)
                except Exception:
                    parsed_data = None
                if parsed_data is None:
                    message.pop("data")
                else:
                    message["data"] = parsed_data
        return {
            "message": message,
            "exit_code": exit_code
        }

    @classmethod
    def _read_state_flag(cls, msg: str) -> dict[str, Any]:
        msg_ = msg.split(".")
        return {
            "message": msg_[0],
            "exit_code": 0
        }
