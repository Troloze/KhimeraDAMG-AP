from __future__ import annotations

import logging
import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import Utils
from CommonClient import ClientStatus
from NetUtils import NetworkItem
from platformdirs import user_data_dir

if TYPE_CHECKING:
    from .client import KhimeraDAMGContext

logger = logging.getLogger("Client")

class KhimeraCommunicationHandler:
    # Will host the pooling thread
    def __init__(self, host_version: str, ctx: KhimeraDAMGContext) -> None:
        self.contract: type[CommunicationContract] = get_contract(host_version)
        self.client_ctx: KhimeraDAMGContext = ctx

    def update_host_connection_status(self, _is_connected: bool) -> None:
        pass

    def send_deathlink(self) -> None:
        if not self.is_connected():
            return

    async def on_deathlink(self) -> None:
        await self.client_ctx.send_death("")

    def on_goal(self) -> None:
        self.client_ctx.finished_game = True
        Utils.async_start(self.client_ctx.send_msgs(
        [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]))

    def is_connected(self) -> bool:
        # Thread safe implementation
        raise NotImplementedError

# All changes made here must be retrocompatible.
class CommunicationEvent:
    @dataclass(frozen=True)
    class Event:
        def validate_version(self, version: str):
            values: list[str] = version.split(".")
            error = ValueError('Version has to contain only 3 non negative integers separated by dots. (i.e., "X.Y.Z")')
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

        def validate_string(self, string: str):
            if not string.isascii():
                raise ValueError("All string values should be ascii compliant.")

        def validate_string_space(self, string: str):
            if not string.isascii():
                raise ValueError("All string values should be ascii compliant.")
            if any(c.isspace() for c in string):
                raise ValueError("Attempted to set a parameter to a string with a space character.")

        def validate_int_non_negative(self, value: int):
            if value < 0:
                raise ValueError("Attempted to set a negative value to a non negative field.")

        def validate_bool(self, value: int):
            if value not in [0, 1]:
                raise ValueError("Attempted to set an invalid value to a boolean field that takes only 0 or 1.")

        def validate_option_data(self, value: int | str | list[int | str]):
            if isinstance(value, int):
                return
            if isinstance(value, str):
                self.validate_string_space(value)
                return
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, int):
                        continue
                    if isinstance(entry, str):
                        self.validate_string_space(entry)
                        continue
                    raise TypeError(f"Invalid type in value list: {type(entry).__name__}")
                return
            raise TypeError(f"Invalid value type: {type(value).__name__}")

        def sanitize_string(self, value: str, value_name: str):
            # Value is validated for ascii before going here,
            # so it is guaranteed ascii.
            sanitized_value = value.replace("#", "\\#")
            sanitized_value = re.sub(r"(?! )\s", "", sanitized_value)
            object.__setattr__(self, value_name, sanitized_value)

        def sanitize_option_data(self, value: int | str | list[int | str], value_name):
            # List is validated for type, spaces and ascii before going here.
            if isinstance(value, int):
                return
            if isinstance(value, str):
                self.sanitize_string(value, value_name)
                return
            sanitized_list: list[int | str] = []
            for entry in value:
                if isinstance(entry, int):
                    sanitized_list.append(entry)
                else:
                    sanitized_list.append(entry.replace("#", "\\#"))
            object.__setattr__(self, value_name, sanitized_list)

    @dataclass(frozen=True)
    class Empty(Event):
        pass

    @dataclass(frozen=True)
    class ApVersion(Event):
        version: str

        def __post_init__(self):
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class ClientWorldVersion(Event):
        version: str

        def __post_init__(self):
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class HostWorldVersion(Event):
        version: str

        def __post_init__(self):
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class SlotName(Event):
        name: str

        def __post_init__(self):
            self.validate_string(self.name)
            self.sanitize_string(self.name, "name")

    @dataclass(frozen=True)
    class ApOption(Event):
        name: str
        value: int | str | list[int | str]

        def __post_init__(self):
            self.validate_string_space(self.name)
            self.validate_option_data(self.value)
            self.sanitize_string(self.name, "name")
            self.sanitize_option_data(self.value, "value")

    @dataclass(frozen=True)
    class SlotData(Event):
        name: str
        value: int | str | list[int | str]

        def __post_init__(self):
            self.validate_string_space(self.name)
            self.validate_option_data(self.value)
            self.sanitize_string(self.name, "name")
            self.sanitize_option_data(self.value, "value")

    @dataclass(frozen=True)
    class LastAck(Event):
        value: int

        def __post_init__(self):
            self.validate_int_non_negative(self.value)

    @dataclass(frozen=True)
    class ItemReceived(Event):
        item_id: int
        order_received: int

        def __post_init__(self):
            self.validate_int_non_negative(self.item_id)
            self.validate_int_non_negative(self.order_received)

    @dataclass(frozen=True)
    class LocationChecked(Event):
        location_id: int

        def __post_init__(self):
            self.validate_int_non_negative(self.location_id)

    @dataclass(frozen=True)
    class LocationClassificationPreview(Event):
        enabled: int

        def __post_init__(self):
            self.validate_bool(self.enabled)

    @dataclass(frozen=True)
    class LocationClassification(Event):
        location_id: int
        item_classification: int
        player_id: int

        def __post_init__(self):
            self.validate_int_non_negative(self.location_id)
            self.validate_int_non_negative(self.item_classification)
            self.validate_int_non_negative(self.player_id)

    @dataclass(frozen=True)
    class Message(Event):
        message: str

        def __post_init__(self):
            self.validate_string(self.message)
            self.sanitize_string(self.message, "message")

    @dataclass(frozen=True)
    class DeathLink(Event):
        message: str

        def __post_init__(self):
            self.validate_string(self.message)
            self.sanitize_string(self.message, "message")

    @dataclass(frozen=True)
    class Ack(Event):
        value: int

        def __post_init__(self):
            self.validate_int_non_negative(self.value)

    @dataclass(frozen=True)
    class Win(Event):
        pass

    @dataclass(frozen=True)
    class ConnectionStatus(Event):
        value: int

        def __post_init__(self):
            self.validate_bool(self.value)

    @dataclass(frozen=True)
    class Heartbeat(Event):
        value: int

        def __post_init__(self):
            self.validate_int_non_negative(self.value)

class CommunicationContract(metaclass=ABCMeta):
    # Parent class for all communication contracts
    @classmethod
    @abstractmethod
    def write_content(cls, content_type: str, params: dict[str, Any]) -> tuple[str, int]:
        pass

    @classmethod
    @abstractmethod
    def read_content(cls, content_type: str, content: str) -> dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def parse_message(cls, msg: str) -> tuple[list[CommunicationEvent.Event], int]:
        pass

    @classmethod
    @abstractmethod
    def parse_events(cls, events: list[CommunicationEvent.Event]) -> tuple[str, int]:
        pass

    @classmethod
    @abstractmethod
    def get_sandbox_folder(cls) -> Path:
        pass

unknown_event_set: set[type[CommunicationEvent.Event]] = set()
unknown_option_set: set[str] = set()
unknown_data_set: set[str] = set()
unknown_flag_set: set[str] = set()

class ContractV1(CommunicationContract):
    class EventSerializer:
        class OptionSerializer:
            # Assumes the chosen option will be passed as an int value
            @staticmethod
            def choice(option: tuple[str, Any]) -> str:
                name: str = option[0]
                value: int = int(option[1])
                if value < 0:
                    raise ValueError(f'Option "{name}" of type choice has a negative value.')
                return f"OPTION {name} S {value}"

            # Assumes 0 is False and 1 is True
            # int(False) returns 0, int(True) returns 1.
            @staticmethod
            def toggle(option: tuple[str, Any]) -> str:
                name: str = option[0]
                value: int = int(option[1])
                if value not in [0, 1]:
                    raise ValueError("Toggle values must be either 0 or 1")
                return f"OPTION {name} S {value}"

            # A single integer value.
            @staticmethod
            def range(option: tuple[str, Any]) -> str:
                name: str = option[0]
                value: int = int(option[1])
                return f"OPTION {name} S {value}"

            @staticmethod
            def op_list(option: tuple[str, Any]) -> str:
                name: str = option[0]
                values: list[str | int] = option[1]
                ret = f"OPTION {name} L {len(values)}"
                if len(values) > 1:
                    v_type = type(values[0])
                    if not all(isinstance(entry, v_type) for entry in values):
                        raise TypeError("Every entry in an option list should be of the same type.")
                for value in values:
                    if isinstance(value, str):
                        if any(c.isspace() for c in value):
                            raise ValueError("Option list string values cannot contain whitespaces.")
                        _value = str(value)
                    elif isinstance(value, int):
                        _value = int(value)
                    else:
                        raise TypeError("Option lists should only contain integers or strings.")
                    ret += f" {_value}"
                return ret

            @staticmethod
            def op_set(option: tuple[str, Any]) -> str:
                name: str = option[0]
                values: list[str] = list(option[1]) # validates type and allows to be sorted.
                values.sort() # Spec defines these to be sorted
                ret = f"OPTION {name} L {len(values)}"
                for value in values:
                    if isinstance(value, str) and any(c.isspace() for c in value):
                        raise ValueError("List string values cannot contain whitespaces")
                    ret += f" {value}"
                return ret

            # Contract expects values to be sorted.
            @staticmethod
            def op_count(option: tuple[str, Any]) -> str:
                name: str = option[0]
                values: dict[str, Any] = option[1]
                ret = f"OPTION {name} D {len(values)}"
                for key, value in sorted(values.items()): # Spec defines these to be sorted
                    if any(c.isspace() for c in key):
                        raise ValueError("Dict keys cannot contain whitespaces")
                    if isinstance(value, int):
                        ret += f" {key} {int(value)}"
                    else:
                        raise ValueError(f'Option "{name}" of type count has non integer value on key "{key}".')
                return ret

        class DataSerializer:
            @staticmethod
            def int_value(data: tuple[str, Any]) -> str:
                name: str = data[0]
                value: int = int(data[1])
                return f"DATA {name} S {value}"

            @staticmethod
            def bool_value(data: tuple[str, Any]) -> str:
                name: str = data[0]
                value: int = int(data[1])
                if value not in [0, 1]:
                    raise ValueError("Bool values should be either 0 or 1.")
                return f"DATA {name} S {value}"

            @staticmethod
            def str_value(data: tuple[str, Any]) -> str:
                name: str = data[0]
                value: str = str(data[1])
                if any(c.isspace() for c in value):
                    raise ValueError("Strings cannot contain whitespaces")
                return f"DATA {name} S {value}"

            @staticmethod
            def list_value(data: tuple[str, Any]) -> str:
                name: str = data[0]
                values: list[int | str] = data[1]
                ret = f"DATA {name} L {len(values)}"
                if len(values) > 1:
                    v_type = type(values[0])
                    if not all(isinstance(value, v_type) for value in values):
                        raise TypeError("Data lists should not contain both integer and string values.")
                for value in values:
                    if isinstance(value, str):
                        if any(c.isspace() for c in value):
                            raise ValueError("Data list string values cannot contain whitespaces.")
                        _value = str(value)
                    elif isinstance(value, int):
                        _value = int(value)
                    else:
                        raise TypeError("Data lists should only contain integers or strings.")
                    ret += f" {_value}"
                return ret

            @staticmethod
            def dict_value(data: tuple[str, Any]) -> str:
                name: str = data[0]
                values: dict[str, Any] = data[1]
                ret = f"DATA {name} D {len(values)}"
                for key, value in sorted(values.items()): # Spec defines these to be sorted
                    if any(c.isspace() for c in key):
                        raise ValueError("Dict keys cannot contain whitespaces")
                    if isinstance(value, int):
                        ret += f" {key} {int(value)}"
                    elif isinstance(value, str):
                        if any(c.isspace() for c in value):
                            raise ValueError("Dict string values cannot contain whitespaces")
                        ret += f" {key} {value!s}"
                    else:
                        raise ValueError(f'Data entry "{name}" of type dict has a non integer \
                                         or string value on key "{key}".')
                return ret

        option_serializers: ClassVar[dict[str, str]] = {
            "choice":               "choice",
            "toggle":               "toggle",
            "default_on_toggle":    "toggle",
            "range":                "range",
            "named_range":          "range",
            "option_list":          "op_list",
            "option_set":           "op_set",
            "option_count":         "op_count"
        }

        option_types: ClassVar[dict[str, str]] = {
            "death_link":               "toggle",
            "victory_condition":        "choice",
            "shuffle_books":            "toggle",
            "shuffle_fairies":          "toggle",
            "shuffle_detonators":       "toggle",
            "shuffle_gourmet_gal":      "toggle",
        }

        data_serializers: ClassVar[dict[str, str]] = {
            "bool":         "bool_value",
            "int":          "int_value",
            "str":          "str_value",
            "list":         "list_value",
            "dict":         "dict_value"
        }

        data_types: ClassVar[dict[str, str]] = {
            # Emtpy for now
        }

        @staticmethod
        def serialize_ap_version(event: CommunicationEvent.ApVersion) -> str:
            return f"APV {event.version}"

        @staticmethod
        def serialize_host_world_version(event: CommunicationEvent.HostWorldVersion) -> str:
            return f"APW {event.version}"

        @staticmethod
        def serialize_client_world_version(event: CommunicationEvent.ClientWorldVersion) -> str:
            return f"CAPW {event.version}"

        @staticmethod
        def serialize_slot_name(event: CommunicationEvent.SlotName) -> str:
            return f"SLOT {event.name}"

        @classmethod
        def serialize_ap_option(cls, event: CommunicationEvent.ApOption) -> str:
            option_type = cls.option_types.get(event.name)
            if option_type is None:
                if event.name not in unknown_option_set:
                    logger.warning(f'Attempted to serialize unknown option named: "{event.name}".')
                    unknown_option_set.add(event.name)
                return ""
            option_serializer_name = cls.option_serializers.get(option_type)
            if option_serializer_name is None:
                raise ValueError(f'Option of type "{option_type}" does not have a defined serializer.')
            return getattr(cls.OptionSerializer, option_serializer_name)((event.name, event.value))

        @classmethod
        def serialize_slot_data(cls, event: CommunicationEvent.SlotData) -> str:
            data_type = cls.data_types.get(event.name)
            if data_type is None:
                if event.name not in unknown_data_set:
                    logger.warning(f'Attempted to serialize unknown data named: "{event.name}".')
                    unknown_data_set.add(event.name)
                return ""
            data_serializer_name = cls.data_serializers.get(data_type)
            if data_serializer_name is None:
                raise ValueError(f'Data of type "{data_type}" does not have a defined serializer.')
            return getattr(cls.DataSerializer, data_serializer_name)((event.name, event.value))

        @staticmethod
        def serialize_last_ack(event: CommunicationEvent.LastAck) -> str:
            return f"LACK {event.value}"

        @staticmethod
        def serialize_item_received(event: CommunicationEvent.ItemReceived) -> str:
            return f"ITEM {event.item_id} {event.order_received}"

        @staticmethod
        def serialize_location_checked(event: CommunicationEvent.LocationChecked) -> str:
            return f"LOC {event.location_id}"

        @staticmethod
        def serialize_location_classification_preview(event: CommunicationEvent.LocationClassificationPreview) -> str:
            return f"LCPV {event.enabled}"

        @staticmethod
        def serialize_location_classification(event: CommunicationEvent.LocationClassification) -> str:
            return f"LC {event.location_id} {event.item_classification} {event.player_id}"

        @staticmethod
        def serialize_message(event: CommunicationEvent.Message) -> str:
            # Message is assumed to be parsed for bad characters
            return f"MSG {event.message}"

        @staticmethod
        def serialize_death_link(event: CommunicationEvent.DeathLink) -> str:
            # Message is assumed to be parsed for bad characters
            return f"DLINK {event.message}"

        @staticmethod
        def serialize_ack(event: CommunicationEvent.Ack) -> str:
            return f"ACK {event.value}"

        @staticmethod
        def serialize_win(_event: CommunicationEvent.Win) -> str:
            return "WIN"

        @staticmethod
        def serialize_connection_status(event: CommunicationEvent.ConnectionStatus) -> str:
            return f"STATUS {event.value}"

        @staticmethod
        def serialize_heartbeat(event: CommunicationEvent.Heartbeat) -> str:
            return f"HBEAT {event.value}"

        event_to_parser: ClassVar[dict[type[CommunicationEvent.Event], str]] = {
            CommunicationEvent.ApVersion:                       "serialize_ap_version",
            CommunicationEvent.ClientWorldVersion:              "serialize_client_world_version",
            CommunicationEvent.HostWorldVersion:                "serialize_host_world_version",
            CommunicationEvent.SlotName:                        "serialize_slot_name",
            CommunicationEvent.ApOption:                        "serialize_ap_option",
            CommunicationEvent.SlotData:                        "serialize_slot_data",
            CommunicationEvent.LastAck:                         "serialize_last_ack",
            CommunicationEvent.ItemReceived:                    "serialize_item_received",
            CommunicationEvent.LocationChecked:                 "serialize_location_checked",
            CommunicationEvent.LocationClassificationPreview:   "serialize_location_classification_preview",
            CommunicationEvent.LocationClassification:          "serialize_location_classification",
            CommunicationEvent.Message:                         "serialize_message",
            CommunicationEvent.DeathLink:                       "serialize_death_link",
            CommunicationEvent.Ack:                             "serialize_ack",
            CommunicationEvent.Win:                             "serialize_win",
            CommunicationEvent.ConnectionStatus:                "serialize_connection_status",
            CommunicationEvent.Heartbeat:                       "serialize_heartbeat",
        }

        @classmethod
        def serialize_event(cls, event: CommunicationEvent.Event) -> str:
            event_type = type(event)
            parser_name = cls.event_to_parser.get(event_type)
            if parser_name is None:
                if event_type not in unknown_event_set:
                    logger.warning(f'Attempted to serialize unknown event of type: "{event_type.__name__}.')
                    unknown_event_set.add(event_type)
                return ""
            ret: str = getattr(cls, parser_name)(event)
            if not ret.isascii():
                # Should always be called, even if spammed. This is a client side issue that
                # should be known and resolved.
                logger.warning(f'"{event_type.__name__}" event serialization resulted in a non-ascii row:\n"{ret}"')
            return ret.encode("ascii", "replace").decode("ascii")

        @classmethod
        def parse(cls, events: list[CommunicationEvent.Event]) -> tuple[str, int]:
            """ Transforms an event list into a string.
            Returns a tuple with the output string and an exit code.\n
            Exit code 0 is success; exit code 1 means at least one event was not parsed.
            """
            event_strings: list[str] = [cls.serialize_event(event) for event in events] + ["$"]
            exit_code = 0
            if any(True for entry in event_strings if entry == ""):
                exit_code = 1
            return (
                "\n".join([entry for entry in event_strings if entry != ""]),
                exit_code
            )

    class EventDeserializer:
        @staticmethod
        def deserialize_ap_version(row: list[str]) -> CommunicationEvent.ApVersion | None:
            if len(row) <= 1:
                return None
            return CommunicationEvent.ApVersion(row[1])

        @staticmethod
        def deserialize_client_world_version(row: list[str]) -> CommunicationEvent.ClientWorldVersion | None:
            if len(row) <= 1:
                return None
            return CommunicationEvent.ClientWorldVersion(row[1])

        @staticmethod
        def deserialize_host_world_version(row: list[str]) -> CommunicationEvent.HostWorldVersion | None:
            if len(row) <= 1:
                return None
            return CommunicationEvent.HostWorldVersion(row[1])

        @staticmethod
        def deserialize_slot_name(row: list[str]) -> CommunicationEvent.SlotName | None:
            if len(row) <= 1:
                return None
            # Reads raw string, nothing to evaluate here
            return CommunicationEvent.SlotName(row[1])

        @staticmethod
        def deserialize_ap_option(_row: list[str]) -> CommunicationEvent.ApOption | None:
            # The game shouldn't ever send an option to the client, I won't bother setting this up.
            return None

        @staticmethod
        def deserialize_slot_data(_row: list[str]) -> CommunicationEvent.SlotData | None:
            # The game shouldn't ever send slot data to the client, I won't bother setting this up.
            return None

        @staticmethod
        def deserialize_last_ack(row: list[str]) -> CommunicationEvent.LastAck | None:
            if len(row) <= 1:
                return None
            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.LastAck(param_1)

        @staticmethod
        def deserialize_item_received(row: list[str]) -> CommunicationEvent.ItemReceived | None:
            if len(row) <= 2:
                return None

            try:
                param_1: int = int(row[1])
                param_2: int = int(row[2])
            except ValueError:
                return None

            return CommunicationEvent.ItemReceived(param_1, param_2)

        @staticmethod
        def deserialize_location_checked(row: list[str]) -> CommunicationEvent.LocationChecked | None:
            if len(row) <= 1:
                return None

            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.LocationChecked(param_1)

        @staticmethod
        def deserialize_location_classification_preview(
            row: list[str]
        ) -> CommunicationEvent.LocationClassificationPreview | None:
            if len(row) <= 1:
                return None

            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.LocationClassificationPreview(param_1)

        @staticmethod
        def deserialize_location_classification(row: list[str]) -> CommunicationEvent.LocationClassification | None:
            if len(row) <= 3:
                return None

            try:
                param_1: int = int(row[1])
                param_2: int = int(row[2])
                param_3: int = int(row[3])
            except ValueError:
                return None

            return CommunicationEvent.LocationClassification(param_1, param_2, param_3)

        @staticmethod
        def deserialize_message(row: list[str]) -> CommunicationEvent.Message | None:
            if len(row) <= 1:
                return None
            return CommunicationEvent.Message(" ".join(row[1:]))

        @staticmethod
        def deserialize_death_link(row: list[str]) -> CommunicationEvent.DeathLink | None:
            if len(row) <= 1:
                # return None
                # A message-less death link could happen.
                pass
            return CommunicationEvent.DeathLink(" ".join(row[1:]))

        @staticmethod
        def deserialize_ack(row: list[str]) -> CommunicationEvent.Ack | None:
            if len(row) <= 1:
                return None

            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.Ack(param_1)

        @staticmethod
        def deserialize_win(_row: list[str]) -> CommunicationEvent.Win | None:
            return CommunicationEvent.Win()

        @staticmethod
        def deserialize_connection_status(row: list[str]) -> CommunicationEvent.ConnectionStatus | None:
            if len(row) <= 1:
                return None

            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.ConnectionStatus(param_1)

        @staticmethod
        def deserialize_heartbeat(row: list[str]) -> CommunicationEvent.Heartbeat | None:
            if len(row) <= 1:
                return None

            try:
                param_1 = int(row[1])
            except ValueError:
                return None

            return CommunicationEvent.Heartbeat(param_1)

        flag_to_parser: ClassVar[dict[str, str]] = {
            "APV":      "deserialize_ap_version",
            "APW":      "deserialize_host_world_version",
            "CAPW":     "deserialize_client_world_version",
            "SLOT":     "deserialize_slot_name",
            "OPTION":   "deserialize_ap_option",
            "DATA":     "deserialize_slot_data",
            "LACK":     "deserialize_last_ack",
            "ITEM":     "deserialize_item_received",
            "LOC":      "deserialize_location_checked",
            "LCPV":     "deserialize_location_classification_preview",
            "LC":       "deserialize_location_classification",
            "MSG":      "deserialize_message",
            "DLINK":    "deserialize_death_link",
            "ACK":      "deserialize_ack",
            "WIN":      "deserialize_win",
            "STATUS":   "deserialize_connection_status",
            "HBEAT":    "deserialize_heartbeat",

        }

        @classmethod
        def deserialize_line(cls, message: str) -> CommunicationEvent.Event | None:
            row = message.replace("\\#", "#").split(" ")
            ignored_identifiers = ["", "$"]
            if row[0] in ignored_identifiers:
                return CommunicationEvent.Empty()

            parser_name = cls.flag_to_parser.get(row[0])
            if parser_name is None:
                if row[0] not in unknown_flag_set:
                    logger.warning(f'Attempted to deserialize unknown flag: "{row[0]!s}".')
                    unknown_flag_set.add(row[0])
                return None
            return getattr(cls, parser_name)(row)

        @classmethod
        def parse(cls, message: str) -> tuple[list[CommunicationEvent.Event], int]:
            """ Transforms a message into a list of events.
            Returns a tuple with the event list, and an exit code.\n
            Exit code is an int flag:\n
            - bit 1: at least one line was either malformed or not recognized.\n
            - bit 2: the file was incomplete.
            """
            rows = message.splitlines()
            if len(rows) == 0:
                return ([], 2)
            exit_code = 0 if rows[-1] == "$" else 2
            deserialized = [cls.deserialize_line(row) for row in rows]
            if None in deserialized:
                exit_code += 1
            return (
                [row for row in deserialized if row is not None and not isinstance(row, CommunicationEvent.Empty)],
                exit_code
            )

    max_messages_per_tick: ClassVar[int] = 50

    @classmethod
    def write_context(cls, params: dict[str, Any]) -> tuple[str, int]:
        ap_version: str = params["ap_version"]
        host_world_version: str = params["host_world_version"]
        client_world_version: str = params["client_world_version"]
        slot_name: str = params["slot_name"]
        last_ack: int = params["last_ack"]
        options: dict[str, Any] = params["options"]
        slot_data: dict[str, Any] = params["slot_data"]
        locations: set[int] = params["locations"]
        item_list: list[tuple[int, NetworkItem]] = params["item_list"]
        has_goaled: bool = params["has_goaled"]

        event_ap_version = CommunicationEvent.ApVersion(ap_version)
        event_host_world_version = CommunicationEvent.HostWorldVersion(host_world_version)
        event_client_world_version = CommunicationEvent.ClientWorldVersion(client_world_version)
        event_slot_name = CommunicationEvent.SlotName(slot_name)
        event_last_ack = CommunicationEvent.LastAck(last_ack)

        events: list[CommunicationEvent.Event] = [
            event_ap_version,
            event_host_world_version,
            event_client_world_version,
            event_slot_name,
            event_last_ack
        ]

        events.extend(CommunicationEvent.ApOption(entry, value) for entry, value in options.items())
        events.extend(CommunicationEvent.SlotData(entry, value) for entry, value in slot_data.items())
        events.extend(CommunicationEvent.LocationChecked(entry) for entry in locations)
        events.extend(CommunicationEvent.ItemReceived(item[1].item, item[0]) for item in item_list)

        if has_goaled:
            events.append(CommunicationEvent.Win())

        return cls.parse_events(events)

    @classmethod
    def write_location_information(cls, params: dict[str, Any]) -> tuple[str, int]:
        enabled: bool = params["enabled"]

        if not enabled:
            return cls.parse_events([CommunicationEvent.LocationClassificationPreview(0)])

        loc_info: dict[int, tuple[int, int]] | None = params["loc_info"]

        ret: list[CommunicationEvent.Event] = [CommunicationEvent.LocationClassificationPreview(1)]
        if loc_info is None:
            return cls.parse_events(ret)
        for loc_id, loc_data in loc_info.items():
            ret.append(CommunicationEvent.LocationClassification(loc_id, loc_data[0], loc_data[1]))

        return cls.parse_events(ret)

    @classmethod
    def write_connection_state(cls, params: dict[str, Any]) -> tuple[str, int]:
        status: int = params["status"]
        heartbeat: int = params["heartbeat"]
        return cls.parse_events([
            CommunicationEvent.ConnectionStatus(status),
            CommunicationEvent.Heartbeat(heartbeat)
        ])

    @classmethod
    def write_host_info(cls, params: dict[str, Any]) -> tuple[str, int]:
        # Cap the message count
        messages: list[str] = params["messages"][-cls.max_messages_per_tick:]
        items: list[tuple[int, NetworkItem]] = params["items"]
        death_link: list[str] = params["death_link"]
        locations: set[int] = params["locations"]

        ret = []
        ret.extend(CommunicationEvent.Message(msg) for msg in messages)
        ret.extend(CommunicationEvent.ItemReceived(item[1].item, item[0]) for item in items)
        ret.extend(CommunicationEvent.DeathLink(death) for death in death_link)
        ret.extend(CommunicationEvent.LocationChecked(loc) for loc in locations)

        return cls.parse_events(ret)

    @classmethod
    def read_game_info(cls, msg: str) -> dict[str, Any]:
        parsed = cls.parse_message(msg)
        events = parsed[0]
        parse_exit_code = parsed[1]
        is_win: bool = False
        ack: int = -1
        dlink_msgs: list[str] = []

        locations: set[int] = set()

        for event in events:
            match event:
                case CommunicationEvent.LocationChecked():
                    locations.add(event.location_id)
                case CommunicationEvent.DeathLink():
                    dlink_msgs.append(event.message)
                case CommunicationEvent.Win():
                    is_win = True
                case CommunicationEvent.Ack():
                    ack = event.value
        return {
            "locations": locations,
            "deathlink": dlink_msgs,
            "ack": ack,
            "is_win": is_win,
            "exit_code": parse_exit_code
        }

    @classmethod
    def read_game_state(cls, msg: str) -> dict[str, Any]:
        parsed = cls.parse_message(msg)
        events = parsed[0]
        parse_exit_code = parsed[1]
        if (
            parse_exit_code or
            not events or
            not isinstance(events[0], CommunicationEvent.Heartbeat)
        ):
            return {"heartbeat": -1, "exit_code": parse_exit_code}

        return {"heartbeat": events[0].value, "exit_code": parse_exit_code}

    @classmethod
    def write_content(cls, content_type: str, params: dict[str, Any]) -> tuple[str, int]:
        type_to_writer: dict[str, str] = {
            "cctx":     "write_context",
            "ls":       "write_location_information",
            "in":       "write_host_info",
            "cs":       "write_connection_state",
        }
        writer = type_to_writer.get(content_type)
        if writer is None:
            raise ValueError(f"Attempt to create unknown type of content: {content_type}")
        return getattr(cls, writer)(params)

    @classmethod
    def read_content(cls, content_type: str, content: str) -> dict[str, Any]:
        type_to_reader: dict[str, str] = {
            "out":  "read_game_info",
            "gs":   "read_game_state",
        }
        reader = type_to_reader.get(content_type)
        if reader is None:
            raise ValueError(f"Attempt to read unknown type of content: {content_type}")
        return getattr(cls, reader)(content)

    @classmethod
    def parse_events(cls, events: list[CommunicationEvent.Event]) -> tuple[str, int]:
        return cls.EventSerializer.parse(events)

    @classmethod
    def parse_message(cls, msg: str) -> tuple[list[CommunicationEvent.Event], int]:
        return cls.EventDeserializer.parse(msg)

    @classmethod
    def get_sandbox_folder(cls) -> Path:
        return Path(user_data_dir("khimera_ap", False))

version_to_class_id: dict[tuple[int, int, int], type[CommunicationContract]] = {
    (0, 0, 0): ContractV1
}

def get_contract(contract_version: str) -> type[CommunicationContract]:
    digits = tuple(map(int, contract_version.split(".")))
    if len(digits) != 3:
        raise ValueError("Version strings must be composed of 3 numbers separated by dots.")
    # This function is barely ever called and the lookup dictionary will never be big enough.
    # It's ok for this to remain suboptimal.
    key: tuple[int, int, int] | None = max((k for k in version_to_class_id if k <= digits), default=None)
    if key is None:
        raise ValueError("Couldn't find a contract that matches this version. "
                         "(Please don't use negative values in versions)")
    return version_to_class_id[key]
