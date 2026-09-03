from __future__ import annotations

import asyncio
import logging
import queue
from typing import Any

from NetUtils import NetworkItem  # type: ignore

from ..types import ConnectionContext, LocationInformation, RuntimeInformation, RuntimeStatus
from .classes import CommunicationAgent
from .storage import get_agent

__all__ = ["KhimeraDAMGCommunicationInterface"]

logger = logging.getLogger("Client")

class KhimeraDAMGCommunicationInterface:
    send_queue: queue.Queue[tuple[str, Any]]
    get_queue: queue.Queue[tuple[str, Any]]

    def __init__(self) -> None:
        self.send_queue = queue.Queue()
        self.get_queue = queue.Queue()
        self.running = False
        self.agent:CommunicationAgent | None = None
        self.last_heartbeat = -1
        self.session_last_ack = -1

    def send_item(self, item: NetworkItem, order: int) -> None:
        pckg: tuple[str, Any] = ("item", (order, item))

        try:
            self.send_queue.put(pckg)
        except queue.ShutDown:
            pass

    def send_location(self, location_id: int) -> None:
        pckg: tuple[str, Any] = ("location", location_id)

        try:
            self.send_queue.put(pckg)
        except queue.ShutDown:
            pass

    def send_message(self, message: str) -> None:
        pckg: tuple[str, Any] = ("message", message)

        try:
            self.send_queue.put(pckg)
        except queue.ShutDown:
            pass

    def send_death_link(self, message: str) -> None:
        pckg: tuple[str, Any] = ("death_link", message)
        try:
            self.send_queue.put(pckg)
        except queue.ShutDown:
            pass

    def send_connection_status(self, is_connected: bool) -> None:
        pckg: tuple[str, Any] = ("status",  0 if is_connected else 1)

        try:
            self.send_queue.put(pckg)
        except queue.ShutDown:
            pass

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
                htg_q=self.send_queue,
                gth_q=self.get_queue
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
                self.send_queue.shutdown()
                self.get_queue.shutdown()

    async def stop(self) -> None:
        if not self.running:
            return
        self.send_queue.shutdown()
        self.running = False
        # Should stop itself after turning running to false.
        # May keep feeding get_queue after a while if this happens while
        # it reads game information.
        if self.agent is not None:
            self.agent.close_communication()
            await self.agent.wait_exit()
        self.agent = None

    def consume_outgoing(self) -> tuple[RuntimeInformation, RuntimeStatus] | None:
        incoming_data: list[tuple[str, Any]] = []

        while True:
            try:
                incoming_data.append(self.get_queue.get_nowait())
            except queue.Empty:
                break
            except queue.ShutDown:
                return None

        locations: set[int] = set()
        death_link: list[str] = []
        is_win: bool = False

        for entry in incoming_data:
            if entry[0] == "location":
                locations.add(entry[1])
            if entry[0] == "death_link":
                death_link.append(entry[1])
            if entry[0] == "ack":
                nack: int = entry[1]
                if self.session_last_ack < nack:
                    self.session_last_ack = nack
            if entry[0] == "is_win":
                is_win = entry[1]
            if entry[0] == "heartbeat":
                nbeat = entry[1]
                if self.last_heartbeat < nbeat:
                    self.last_heartbeat = nbeat

        ri = RuntimeInformation([], locations, [], death_link, self.session_last_ack, is_win)
        rs = RuntimeStatus(-1, self.last_heartbeat)

        return (ri, rs)

    async def probe_game_status(self, host_world_version: str, timeout: float = 1.0) -> bool:
        agent = get_agent(host_world_version)() # Initialized, not started.
        # Could raise
        return await agent.on_game_status_update(timeout=timeout)
