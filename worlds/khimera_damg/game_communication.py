from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import Utils  # type: ignore
from CommonClient import ClientStatus  # type: ignore

if TYPE_CHECKING:
    from .client import KhimeraDAMGContext

logger = logging.getLogger("Client")


class KhimeraCommunicationHandler:
    # Will host the pooling thread
    def __init__(self, ctx: KhimeraDAMGContext) -> None:
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
