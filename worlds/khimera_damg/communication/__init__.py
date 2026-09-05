from __future__ import annotations

import asyncio
import logging
import queue
from contextlib import suppress
from typing import Any

from NetUtils import NetworkItem  # type: ignore

from ..types import ConnectionContext, LocationInformation, RuntimeInformation
from .classes import CommunicationAgent
from .storage import get_agent

__all__ = ["KhimeraDAMGCommunicationInterface"]

logger = logging.getLogger("Client")


class KhimeraDAMGCommunicationInterface:
    _send_queue: queue.Queue[tuple[str, Any]]
    _get_queue: queue.Queue[tuple[str, Any]]

    def __init__(self) -> None:
        self._send_queue = queue.Queue()
        self._get_queue = queue.Queue()
        self.running = False
        self.agent: CommunicationAgent | None = None
        self.session_last_ack = -1

    def send_item(self, item: NetworkItem, order: int) -> None:
        pckg: tuple[str, Any] = ("item", (order, item))

        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_location(self, location_id: int) -> None:
        pckg: tuple[str, Any] = ("location", location_id)

        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_message(self, sender: int, message: str) -> None:
        pckg: tuple[str, Any] = ("message", (sender, message))

        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_death_link(self, sender: int, death_id: int, message: str) -> None:
        pckg: tuple[str, Any] = ("death_link", (sender, death_id, message))
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_death_ack(self, death_id: int) -> None:
        pckg: tuple[str, Any] = ("death_ack", death_id)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_connection_status(self, is_connected: bool) -> None:
        pckg: tuple[str, Any] = ("status", 0 if is_connected else 1)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    async def start(
        self,
        connection_context: ConnectionContext,
        location_information: LocationInformation
    ) -> None:
        self.host_world_version: str = connection_context.host_world_version
        self.agent = get_agent(self.host_world_version)()
        self.running = True
        self.starter_task = asyncio.create_task(
            self.agent.open_communication(
                connection_context=connection_context,
                location_information=location_information,
                htg_q=self._send_queue,
                gth_q=self._get_queue
            )
        )
        try:
            await self.starter_task
        except (OSError, TypeError, ValueError) as err:
            logger.exception(err)
        finally:
            if not self.agent.inspect_communication():
                # This interface is permanently stopped, create a new one to try again.
                self.running = False
                self.agent.close_communication()
                self._send_queue.shutdown()
                self._get_queue.shutdown()

    async def stop(self) -> None:
        if not self.running:
            return
        self._send_queue.shutdown()
        self.running = False
        # Should stop itself after turning running to false.
        # May keep feeding get_queue after a while if this happens while
        # it reads game information.
        if self.agent is not None:
            self.agent.close_communication()
            await self.agent.wait_exit()
        self.agent = None

    def consume_outgoing(self) -> tuple[RuntimeInformation, tuple[bool, bool]] | None:
        incoming_data: list[tuple[str, Any]] = []

        while True:
            try:
                incoming_data.append(self._get_queue.get_nowait())
            except queue.Empty:
                break
            except queue.ShutDown:
                return None

        locations: set[int] | None = set()
        location_acks: set[int] | None = set()
        death_link: tuple[int, int, str] | None = None
        death_ack: int | None = None
        is_win: bool = False
        req_cctx: bool = False
        req_li: bool = False
        for entry in incoming_data:
            if entry[1] is None:
                continue
            if entry[0] == "location":
                locations.add(entry[1])
            if entry[0] == "death_link":
                death_link = entry[1]
            if entry[0] == "ack":
                nack: int = entry[1]
                if self.session_last_ack < nack:
                    self.session_last_ack = nack
            if entry[0] == "location_ack":
                location_acks.add(entry[1])
            if entry[0] == "death_ack":
                death_ack = entry[1]
            if entry[0] == "is_win":
                is_win = is_win or entry[1]
            if entry[0] == "req_cctx":
                req_cctx = entry[1]
            if entry[0] == "req_li":
                req_li = entry[1]

        death_link_ = [death_link] if death_link is not None else None
        ri = RuntimeInformation(
            locations=locations,
            location_acks=location_acks,
            death_link=death_link_,
            death_ack=death_ack,
            ack=self.session_last_ack,
            is_win=is_win
        )

        return ri, (req_cctx, req_li)

    async def probe_game_status(self, host_world_version: str, timeout: float = 1.0) -> bool:
        agent = get_agent(host_world_version)()  # Initialized, not started.
        # Could raise
        return await agent.on_game_status_update(timeout=timeout)
