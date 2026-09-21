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
        self.host_world_version: str = ""
        self.slot_name: str | None = None
        self.seed: str | None = None
        self.session_last_ack: int = 0
        self.running = False
        self.agent: CommunicationAgent | None = None

    def send_items(self, items: list[tuple[int, NetworkItem]]) -> None:
        for entry in items:
            self.send_item(entry[1], entry[0])

    def send_item(self, item: NetworkItem, order: int) -> None:
        pckg: tuple[str, Any] = ("item", (order, item))
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_locations(self, locations: set[int]) -> None:
        for entry in locations:
            self.send_location(entry)

    def send_location(self, location_id: int) -> None:
        pckg: tuple[str, Any] = ("location", location_id)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_message(self, sender: int, message: str) -> None:
        pckg: tuple[str, Any] = ("message", (sender, message))
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_death_link(self, sender: str, death_id: int, message: str) -> None:
        pckg: tuple[str, Any] = ("death_link", (sender, death_id, message))
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_death_ack(self, death_id: int) -> None:
        pckg: tuple[str, Any] = ("death_ack", death_id)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_data_acks(self, data_ids: list[int]) -> None:
        for entry in data_ids:
            self.send_data_ack(entry)

    def send_data_ack(self, data_id: int) -> None:
        pckg: tuple[str, Any] = ("data_ack", data_id)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def send_connection_status(self, is_connected: bool) -> None:
        pckg: tuple[str, Any] = ("status", int(is_connected))
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def _resend_connection_context(self) -> None:
        pckg: tuple[str, Any] = ("req_cctx", True)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    def _resend_location_information(self) -> None:
        pckg: tuple[str, Any] = ("req_li", True)
        with suppress(queue.ShutDown):
            self._send_queue.put(pckg)

    async def start(
        self,
        connection_context: ConnectionContext,
        location_information: LocationInformation
    ) -> None:
        if self.running:
            return
        self.host_world_version = connection_context.host_world_version
        self.slot_name = connection_context.slot_name
        self.seed = connection_context.seed
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

    def authenticate(self, slot_name: str, seed: str) -> bool:
        """Returns false when the credentials do not match."""
        if self.slot_name is None or self.seed is None:
            return False
        if self.slot_name == slot_name and self.seed == seed:
            return True
        return False

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self._send_queue.shutdown()
        # Should stop itself after turning running to false.
        # May keep feeding get_queue after a while if this happens while
        # it reads game information.
        if self.agent is not None:
            self.agent.close_communication()
            await self.agent.wait_exit()
        self.agent = None

    def consume_outgoing(self) -> RuntimeInformation | None:
        incoming_data: list[tuple[str, Any]] = []

        while True:
            try:
                incoming_data.append(self._get_queue.get_nowait())
            except queue.Empty:
                break
            except queue.ShutDown:
                return None

        locations: set[int] | None = None
        location_acks: set[int] | None = None
        death_link: tuple[str, int, str] | None = None
        death_ack: int | None = None
        is_win: bool | None = False
        data: list[tuple[int, str, Any]] | None = None
        for entry in incoming_data:
            if entry[1] is None:
                continue
            if entry[0] == "location":
                if locations is None:
                    locations = set()
                locations.add(entry[1])
            if entry[0] == "death_link":
                death_link = entry[1]
            if entry[0] == "data":
                if data is None:
                    data = []
                data.append(entry[1])
            if entry[0] == "ack":
                nack: int = entry[1]
                if self.session_last_ack < nack:
                    self.session_last_ack = nack
            if entry[0] == "location_ack":
                if location_acks is None:
                    location_acks = set()
                location_acks.add(entry[1])
            if entry[0] == "death_ack":
                death_ack = entry[1]
            if entry[0] == "is_win":
                is_win = is_win or entry[1]
            if entry[0] == "req_cctx":
                self._resend_connection_context()
            if entry[0] == "req_li":
                self._resend_location_information()

        return RuntimeInformation(
            locations=locations,
            location_acks=location_acks,
            death_link=death_link,
            death_ack=death_ack,
            data=data,
            ack=self.session_last_ack,
            is_win=is_win
        )

    async def probe_game_status(self, host_world_version: str, timeout: float = 1.0) -> bool:
        agent = self.agent if self.agent is not None else get_agent(host_world_version)()
        # Could raise
        return await agent.on_game_status_update(timeout=timeout)
