from __future__ import annotations

import os
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING
from platformdirs import user_data_dir

import Utils
from CommonClient import ClientStatus

if TYPE_CHECKING:
    from .client import KhimeraDAMGContext

class KhimeraCommunicationHandler:
    # Will host the pooling thread
    def __init__(self, contract: type[CommunicationContract], ctx: KhimeraDAMGContext) -> None:
        self.contract: CommunicationContract = contract()
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


def get_contract(contract_version: str) -> type[CommunicationContract]:
    return version_to_class_id[contract_version]

class CommunicationContract(metaclass=ABCMeta):
    # Parent class for all communication contracts

    @abstractmethod
    def get_sandbox_folder(self) -> Path:
        pass

class ContractV1(CommunicationContract):

    def get_sandbox_folder(self) -> Path:
        return Path(user_data_dir("khimera_ap", False)) 

# Currently selecting individually, a better approach would be to create
# version ranges (i.e. from 0.0.2 to 0.1.3 use contract v1 from 0.1.4 to 0.1.7 use patch contract v2, ...)
# but for the purposes of an unfinished skeleton this works fine to illustrate the point.
version_to_class_id: dict[str, type[CommunicationContract]] = {
    "0.0.2": ContractV1
}
