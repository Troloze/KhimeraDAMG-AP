import logging
import queue
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from ..types import ConnectionContext, LocationInformation

logger = logging.getLogger("Client")


# Changes to this class should be exclusively additive, and
# no underscored attribute names should be added here.
class CommunicationContract(metaclass=ABCMeta):
    max_messages_per_tick: ClassVar[int] = 50
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
    def parse_message(cls, msg: str) -> tuple[dict[str, Any], int]:
        pass

    @classmethod
    @abstractmethod
    def parse_events(cls, events: dict[str, Any]) -> tuple[str, int]:
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
