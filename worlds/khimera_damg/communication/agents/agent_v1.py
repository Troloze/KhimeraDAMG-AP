from __future__ import annotations

import asyncio
import logging
import os
import queue
import secrets
import threading
import time
from typing import Any, ClassVar

from NetUtils import NetworkItem  # type: ignore

from ...misc import normalize_and_sanitize
from ...types import ConnectionContext, LocationInformation, RuntimeInformation, RuntimeStatus
from ..classes import CommunicationAgent, CommunicationContract

logger = logging.getLogger("Client")

class AgentV1(CommunicationAgent):
    cleanup_target_files: ClassVar[list[str]] = [
        "ap.cctx",
        "ap.cctx.tmp",
        "ap.cctx.rd",
        "ap.li",
        "ap.li.tmp",
        "ap.li.rd",
        "ap.hi",
        "ap.hi.tmp",
        "ap.hi.rd",
        "ap.gi",
        "ap.gi.tmp",
        "ap.gi.rd",
        "ap.cs",
        "ap.cs.tmp"
    ]

    shutdown_cleanup_exclude: ClassVar[list[str]] = [
        "ap.gi.tmp"  # Not included since game produced tmp files should be invisible to the client
    ]

    async def on_game_status_update(self, timeout: float = 1.0) -> bool:
        async def _loop() -> None:
            first_value = None
            current_value = None
            while True:
                await asyncio.sleep(0.1)
                raw = self.read_file("ap.gs", status=True)
                current_value = self.contract.read_content("gs", raw)["heartbeat"] if raw is not None else None
                if current_value is None or current_value < 0:
                    continue
                if first_value is None:
                    first_value = current_value
                    continue
                if first_value != current_value:
                    break

        task = asyncio.create_task(_loop())

        try:
            if timeout > 0:
                async with asyncio.timeout(timeout):
                    await task
            else:
                await task

            return True
        except TimeoutError:
            # No updates in time
            return False

    async def open_communication(
        self,
        connection_context: ConnectionContext,
        location_information: LocationInformation,
        htg_q: queue.Queue,
        gth_q: queue.Queue
    ) -> None:
        self.htg_q = htg_q # Host-to-Game Queue (send)
        self.gth_q = gth_q # Game-to-Host Queue (get)
        if htg_q.is_shutdown or gth_q.is_shutdown:
            raise ValueError("One of the provided queues has been shutdown.")

        # Cleanup
        self.on_start()

        try:
            await self.send_connection_context(connection_context)
            await self.send_location_information(location_information)
        except OSError as err:
            # Do not start threads, handle this later.
            cctx_path = self.sandbox / "ap.cctx"
            li_path = self.sandbox / "ap.li"
            try:
                cctx_path.unlink(missing_ok=True)
                li_path.unlink(missing_ok=True)
            except OSError as err2:
                raise err2 from err
            raise err

        # No need to hold reference, it is self contained, knows when to stop,
        # is daemon and has an event to check for completion.
        threading.Thread(
            target=self.consume_incomming,
            name="KhimeraDAMG Communication Consumer Loop",
            daemon=True
        ).start()

        self.communication_opened = True

    def close_communication(self) -> None:
        self.communication_closed = True

    def inspect_communication(self) -> bool:
        # Agents currently are disposable, once communication is opened
        # and closed it can't be reopened.
        return self.communication_opened and not self.communication_closed

    async def wait_exit(self) -> None:
        if not self.communication_closed:
            raise RuntimeError('"wait_exit" was called before "issue_stop".')
        await asyncio.to_thread(self.thread_exit.wait, timeout=1.0)

    def __init__(self, communication_contract: type[CommunicationContract]) -> None:
        self.contract = communication_contract
        self.sandbox = self.contract.get_sandbox_folder()
        self.host_information_buffer = None
        self.htg_q = None
        self.gth_q = None
        self.communication_opened = False
        self.communication_closed = False
        self.last_connection_status = 1
        self.test_sandbox_access() # Needs to be on init so game status update can be detected.
        self.thread_exit = threading.Event()

    def on_start(self) -> None:
        for file in self.cleanup_target_files:
            file_path = self.sandbox / file
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                # Leftover data that couldn't be deleted, the readers and writers can handle these.
                continue

    def on_exit(self) -> None:
        for file in [entry for entry in self.cleanup_target_files if entry not in self.shutdown_cleanup_exclude]:
            file_path = self.sandbox / file
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                # Leftover data that will need to be handled on startup next session
                continue

    def consumer(self, heartbeat: int) -> tuple[RuntimeInformation, RuntimeStatus] | None:
        if self.communication_closed or self.htg_q is None or self.htg_q.is_shutdown:
            return None

        outgoing_data: list[tuple[str, Any]] = []

        while True:
            try:
                outgoing_data.append(self.htg_q.get_nowait())
            except queue.Empty:
                break
            except queue.ShutDown:
                return None

        item_list: list[tuple[int, NetworkItem]] = []
        messages: list[str] = []
        locations: set[int] = set()
        death_link: list[str] = []

        # heartbeat and ack should remember their last values instead of
        # sending empty/null/nodata values.

        for entry in outgoing_data:
            if entry[0] == "item":
                item_list.append(entry[1])
            if entry[0] == "location":
                locations.add(entry[1])
            if entry[0] == "message":
                messages.append(entry[1])
            if entry[0] == "death_link":
                death_link.append(entry[1])
            if entry[0] == "status":
                self.last_connection_status = entry[1]

        ri = RuntimeInformation(item_list, locations, messages, death_link, -1, False)
        rs = RuntimeStatus(self.last_connection_status, heartbeat)

        return (ri, rs)

    def consume_incomming(self) -> None:
        tick_count = 0
        try:
            while not self.communication_closed:
                started = time.perf_counter()
                queue_values = self.consumer(tick_count)
                tick_count += 1
                if queue_values is not None:
                    try:
                        self.send_connection_status(queue_values[1])
                    except Exception:
                        logger.exception("Failed to update connection status.")
                    try:
                        self.receive_game_status()
                    except Exception:
                        logger.exception("Failed to receive game status.")
                    try:
                        self.receive_game_information()
                    except Exception:
                        logger.exception("Failed to receive game information.")
                    try:
                        self.send_host_information(queue_values[0])
                    except Exception:
                        logger.exception("Failed to send host information.")
                time.sleep(max(0.0, self.contract.tick_time - (time.perf_counter() - started)))
        finally:
            try:
                self.on_exit()
            finally:
                self.thread_exit.set()

    def test_sandbox_access(self) -> None:
        def loop() -> None:
            if not self.sandbox.is_dir():
                self.sandbox.mkdir(parents=True, exist_ok=True)
            next(self.sandbox.iterdir(), None)

            path = self.sandbox / f"{secrets.token_hex(4)}.apscout"
            while path.is_file():
                path = self.sandbox / f"{secrets.token_hex(4)}.apscout"
            path.write_text("test", encoding="ascii")
            path.unlink()
        err_count = 0
        test_count = 3
        for _ in range(test_count):
            try:
                loop()
            except OSError as err:
                err_count += 1
                if err_count == test_count:
                    raise OSError("Client could not access the sandbox folder.") from err
                continue
            break

    def write_file(self, name: str, data: str, status: bool = False) -> bool:
        base_path = self.sandbox / name
        tmp_path = self.sandbox / f"{name}.tmp"
        if not status:
            if base_path.exists():
                return False
        try:
            tmp_path.write_text(data, encoding="ascii")
            os.replace(tmp_path, base_path)
        except OSError:
            return False

        return True

    def read_file(self, name: str, status: bool = False) -> str | None:
        base_path = self.sandbox / name
        rd_path = self.sandbox / f"{name}.rd"
        old_data: str | None = None

        if status:
            try:
                raw = base_path.read_text()
            except OSError:
                return None
            return normalize_and_sanitize(raw)

        if rd_path.exists():
            # Attempt to recover the stray file
            try:
                old_data = rd_path.read_text()
            except OSError:
                pass

            try:
                rd_path.unlink(missing_ok=True)
            except OSError:
                pass

            if old_data is not None:
                old_data = normalize_and_sanitize(old_data)
                # Drops deathlinks
                old_data = "\n".join(row for row in old_data.splitlines() if "DLINK" not in row[:5])

        if not base_path.exists():
            return old_data

        try:
            base_path.rename(rd_path)
        except FileExistsError:
            # Let's attempt to recover this stray file.
            if old_data is None:
                # Otherwise we already recovered it, but unlink failed.
                try:
                    old_data = rd_path.read_text()
                    rd_path.unlink()
                except OSError:
                    return None

                if old_data is not None:
                    old_data = normalize_and_sanitize(old_data)
                    # Drops deathlinks
                    old_data = "\n".join(row for row in old_data.splitlines() if "DLINK" not in row[:5])

            try:
                # .rd was recovered, otherwise this wouldn't be reachable;
                # we can use replace directly here.
                os.replace(base_path, rd_path)
            except OSError:
                return old_data
        except OSError:
            return old_data

        try:
            data = rd_path.read_text()
        except OSError:
            # Leaves stray, hopefully catched in the next tick.
            return old_data
        data = normalize_and_sanitize(data)

        try:
            rd_path.unlink(missing_ok=True)
        except OSError:
            pass

        if old_data is not None:
            # old data is sanitized for death links already, we can just add these.
            # Client does not read messages.
            data = f"{old_data}\n{data}"

        return data

    async def send_connection_context(self, cctx: ConnectionContext) -> None:
        message, _exit_code = self.contract.write_content("cctx", cctx.to_dict())
        # Doesn't need buffer, just resend the same data in case of error.
        attempts = 0
        while not self.write_file("ap.cctx", message):
            attempts += 1
            await asyncio.sleep(1.0)
            if attempts >= 5: # hardcoded for now, might include in the contract later
                raise OSError("Could not write connection context.")

    async def send_location_information(self, li: LocationInformation) -> None:
        message, _exit_code = self.contract.write_content("li", li.to_dict())
        # Doesn't need buffer, just resend the same data.
        attempts = 0
        while not self.write_file("ap.li", message):
            attempts += 1
            await asyncio.sleep(1.0)
            if attempts >= 5:
                raise OSError("Could not write location information.")

    def send_host_information(self, hi: RuntimeInformation) -> None:
        hi = hi.merge(self.host_information_buffer, merger_first=True)
        cap = self.contract.max_messages_per_tick

        pruned_messages = hi.messages[-cap:]
        self.host_information_buffer = RuntimeInformation(
            item_list=hi.item_list,
            locations=hi.locations,
            messages=pruned_messages,
            death_link=hi.death_link,
            ack=hi.ack,         # Not used in host information, but required by the constructor
            is_win=hi.is_win    # Not used in host information, but required by the constructor
        )

        if not (
            self.host_information_buffer.item_list or
            self.host_information_buffer.locations or
            self.host_information_buffer.messages or
            self.host_information_buffer.death_link
        ):
            return

        message, _exit_code = self.contract.write_content("hi", self.host_information_buffer.to_dict("host"))

        if self.write_file("ap.hi", message):
            self.host_information_buffer = None

    def send_connection_status(self, gs: RuntimeStatus) -> None:
        message, _exit_code = self.contract.write_content("cs", gs.to_dict())
        # Doesn't need a buffer or a loop.
        self.write_file("ap.cs", message, status=True)

    def receive_game_information(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        raw: str | None = self.read_file("ap.gi")
        # Could not open file, try again next tick.
        if raw is None:
            return

        game_information: dict[str, Any] = self.contract.read_content("gi", raw)
        locations: set[int] = game_information["locations"]
        death_link: list[str] = game_information["death_link"]
        ack: int = game_information["ack"]
        is_win: bool = game_information["is_win"]
        _exit_code: int = game_information["exit_code"] # Currently does nothing

        for entry in locations:
            self.gth_q.put(("location", entry))
        for entry in death_link:
            self.gth_q.put(("death_link", entry))
        if ack != -1: # Corrupted acks should be ignored.
            self.gth_q.put(("ack", ack))
        self.gth_q.put(("is_win", is_win))

    def receive_game_status(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        raw: str | None = self.read_file("ap.gs", status=True)
        # Could not open file, try again next tick.
        if raw is None:
            return

        game_status = self.contract.read_content("gs", raw)
        heartbeat = game_status["heartbeat"]
        _exit_code: int = game_status["exit_code"] # Currently does nothing

        if heartbeat != -1: # Corrupted heartbeats should be ignored
            self.gth_q.put(("heartbeat", heartbeat))
