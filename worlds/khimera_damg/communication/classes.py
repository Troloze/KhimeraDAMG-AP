import logging
import queue
import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from ..misc import normalize_and_sanitize
from ..types import ConnectionContext, LocationInformation

logger = logging.getLogger("Client")

class EventTypeError(TypeError):
    pass

class EventValueError(ValueError):
    pass

# Changes to this class should be exclusively additive, and
# no underscored attribute names should be added here.
class CommunicationEvent:
    @dataclass(frozen=True)
    class Event:
        invalid: bool = field(default=False, kw_only=True, compare=False, repr=False)
        validate_enabled: bool = field(default=True, kw_only=True, compare=False, repr=False)
        sanitize_enabled: bool = field(default=True, kw_only=True, compare=False, repr=False)

        def __post_init__(self):
            if self.invalid:
                object.__setattr__(self, "validate_enabled", False)
                object.__setattr__(self, "sanitize_enabled", False)

        def validate_version(self, version: str) -> None:
            if not self.validate_enabled:
                return
            values: list[str] = version.split(".")
            error = EventValueError(
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

        def validate_int_non_negative(self, value: int) -> None:
            if not self.validate_enabled:
                return
            if value < 0:
                raise EventValueError("Attempted to set a negative value to a non negative field.")

        def validate_bool(self, value: int) -> None:
            if not self.validate_enabled:
                return
            if value not in [0, 1]:
                raise EventValueError("Attempted to set an invalid value to a boolean field that takes only 0 or 1.")

        def sanitize_string(
                self,
                value: str,
                value_name: str,
                *,
                set_attribute: bool = True,
                validate_space: bool = False
        ) -> str:
            if not (self.sanitize_enabled or self.validate_enabled):
                return ""
            spacing_fixed = re.sub(r"(?! )\s", "", value)
            octothorpe_fixed = spacing_fixed.replace("#", "\\#")
            sanitized_value = normalize_and_sanitize(octothorpe_fixed)
            if set_attribute:
                object.__setattr__(self, value_name, sanitized_value)

            if validate_space and self.validate_enabled:
                if any(c.isspace() for c in sanitized_value):
                    raise EventValueError("Attempted to set a parameter to a string with a space character.")
            return sanitized_value

        def sanitize_option_data(
                self,
                value:
                    int |
                    str |
                    list[int | str] |
                    dict[str, int | str],
                value_name: str
            ) -> None:
            if isinstance(value, int):
                return
            if isinstance(value, str):
                self.sanitize_string(value, value_name, set_attribute=self.sanitize_enabled, validate_space=True)
                return
            if isinstance(value, list):
                sanitized_list: list[int | str] = []
                for entry in value:
                    if isinstance(entry, int):
                        if self.sanitize_enabled:
                            sanitized_list.append(entry)
                    elif isinstance(entry, str):
                        if self.sanitize_enabled:
                            sanitized_entry = self.sanitize_string(entry, "", set_attribute=False, validate_space=True)
                            sanitized_list.append(sanitized_entry)
                    else:
                        if self.validate_enabled:
                            raise EventTypeError(f"Invalid type in list value: {type(entry).__name__}")
                if self.sanitize_enabled:
                    object.__setattr__(self, value_name, sanitized_list)
                return
            if isinstance(value, dict):
                sanitized_key = ""
                sanitized_dict: dict[str, int | str] = {}
                for key, entry in value.items():
                    if not isinstance(key, str):
                        raise EventTypeError(f"Invalid type in dict key: {type(entry).__name__}")
                    if self.sanitize_enabled:
                        sanitized_key = self.sanitize_string(key, "", set_attribute=False, validate_space=True)
                    if isinstance(entry, int):
                        if self.sanitize_enabled:
                            sanitized_dict[sanitized_key] = entry
                    elif isinstance(entry, str):
                        if self.sanitize_enabled:
                            sanitized_entry = self.sanitize_string(entry, "", set_attribute=False, validate_space=True)
                            sanitized_dict[sanitized_key] = sanitized_entry
                    else:
                        if self.validate_enabled:
                            raise EventTypeError(f"Invalid type in dict value: {type(entry).__name__}")
                if self.sanitize_enabled:
                    object.__setattr__(self, value_name, sanitized_dict)
                return
            raise EventTypeError(f"Invalid type: {type(value).__name__}")


    @dataclass(frozen=True)
    class Empty(Event):
        pass

    @dataclass(frozen=True)
    class ApVersion(Event):
        version: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class ClientWorldVersion(Event):
        version: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class HostWorldVersion(Event):
        version: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_version(self.version)

    @dataclass(frozen=True)
    class SlotName(Event):
        name: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.sanitize_string(self.name, "name")

    @dataclass(frozen=True)
    class ApOption(Event):
        name: str
        value: int | str | list[int | str] | dict[str, int | str]

        def __post_init__(self) -> None:
            super().__post_init__()
            self.sanitize_string(self.name, "name", validate_space=True)
            self.sanitize_option_data(self.value, "value")

    @dataclass(frozen=True)
    class SlotData(Event):
        name: str
        value: int | str | list[int | str] | dict[str, int | str]

        def __post_init__(self) -> None:
            super().__post_init__()
            self.sanitize_string(self.name, "name", validate_space=True)
            self.sanitize_option_data(self.value, "value")

    @dataclass(frozen=True)
    class LastAck(Event):
        value: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.value)

    @dataclass(frozen=True)
    class ItemReceived(Event):
        item_id: int
        order_received: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.item_id)
            self.validate_int_non_negative(self.order_received)

    @dataclass(frozen=True)
    class LocationChecked(Event):
        location_id: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.location_id)

    @dataclass(frozen=True)
    class LocationClassificationPreview(Event):
        enabled: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_bool(self.enabled)

    @dataclass(frozen=True)
    class LocationClassification(Event):
        location_id: int
        item_classification: int
        player_id: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.location_id)
            self.validate_int_non_negative(self.item_classification)
            self.validate_int_non_negative(self.player_id)

    @dataclass(frozen=True)
    class Message(Event):
        message: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.sanitize_string(self.message, "message")

    @dataclass(frozen=True)
    class DeathLink(Event):
        message: str

        def __post_init__(self) -> None:
            super().__post_init__()
            self.sanitize_string(self.message, "message")

    @dataclass(frozen=True)
    class Ack(Event):
        value: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.value)

    @dataclass(frozen=True)
    class Win(Event):
        pass

    @dataclass(frozen=True)
    class ConnectionStatus(Event):
        value: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_bool(self.value)

    @dataclass(frozen=True)
    class Heartbeat(Event):
        value: int

        def __post_init__(self) -> None:
            super().__post_init__()
            self.validate_int_non_negative(self.value)

# Changes to this class should be exclusively additive, and
# no underscored attribute names should be added here.
class CommunicationContract(metaclass=ABCMeta):
    max_messages_per_tick: ClassVar[int]  = 50
    tick_time: ClassVar[float] = 0.1

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


class CommunicationAgent(metaclass=ABCMeta):
    @abstractmethod
    async def on_game_status_update(self, timeout: float = 1.0) -> bool:
        pass

    @abstractmethod
    def inspect_communication(self) -> bool:
        pass

    @abstractmethod
    async def open_communication(
        self,
        connection_context: ConnectionContext,
        location_information: LocationInformation,
        htg_q: queue.Queue,
        gth_q: queue.Queue
    ) -> None:
        pass

    @abstractmethod
    def close_communication(self) -> None:
        pass

    @abstractmethod
    async def wait_exit(self) -> None:
        pass

    @abstractmethod
    def __init__(self, communication_contract: type[CommunicationContract]) -> None:
        pass
