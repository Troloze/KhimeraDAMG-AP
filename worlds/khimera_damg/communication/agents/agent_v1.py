from __future__ import annotations

import asyncio
import logging
import os
import queue
import secrets
import threading
import time
from contextlib import suppress
from json import JSONDecodeError
from typing import Any, ClassVar

from NetUtils import NetworkItem  # type: ignore

from ...types import ConnectionContext, LocationInformation, RuntimeInformation
from ..classes import CommunicationAgent, CommunicationContract

logger = logging.getLogger("Client")

unknown_path_set = set()


class AgentV1(CommunicationAgent):
    _cleanup_target_files: ClassVar[list[str]] = [
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
    ]

    _shutdown_cleanup_exclude: ClassVar[list[str]] = [
        "ap.gi.tmp"  # Not included since game produced tmp files should be invisible to the client
    ]

    _max_heartbeat_timeout: ClassVar[float] = 2.5

    async def on_game_status_update(self, timeout: float = 1.0) -> bool:
        async def _loop() -> None:
            first = None
            while True:
                await asyncio.sleep(0.1)
                path_list = self.sandbox.glob("*.gshb")
                try:
                    beat_file = next(path_list)
                except StopIteration:
                    # No .gshb files in the sandbox folder
                    continue

                with suppress(StopIteration):
                    next(path_list)
                    # Stop iteration didn't raise, so there are multiple files.
                    # Should be read as no-data
                    continue

                raw = self.contract.read_content("gshb", beat_file.name)

                try:
                    beat = int(raw["message"])
                except ValueError:
                    if beat_file not in unknown_path_set:
                        unknown_path_set.add(beat_file)
                        logger.warning(f"Unexpected flag name: {beat_file}")
                    # Unknown value error
                    return

                if first is None:
                    first = beat
                    continue
                if first == beat:
                    continue
                return
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
        self.htg_q = htg_q  # Host-to-Game Queue (send)
        self.gth_q = gth_q  # Game-to-Host Queue (get)
        if htg_q.is_shutdown or gth_q.is_shutdown:
            raise ValueError("One of the provided queues has been shutdown.")

        # Cleanup
        self._on_start()

        try:
            await self._send_connection_context(connection_context)
            await self._send_location_information(location_information)
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
            target=self._consume_incoming,
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
        self.last_game_heartbeat: int = -1
        self.time_since_last_heartbeat_update: float = -1
        self._test_sandbox_access()  # Needs to be on init so game status update can be detected.
        self.thread_exit = threading.Event()

    def _on_start(self) -> None:
        for file in self._cleanup_target_files:
            file_path = self.sandbox / file
            with suppress(OSError):
                file_path.unlink(missing_ok=True)
        paths = self.sandbox.glob("*.cs*")
        for path in paths:
            with suppress(OSError):
                path.unlink(missing_ok=True)

    def _on_exit(self) -> None:
        for file in [entry for entry in self._cleanup_target_files if entry not in self._shutdown_cleanup_exclude]:
            file_path = self.sandbox / file
            with suppress(OSError):
                file_path.unlink(missing_ok=True)
        paths = self.sandbox.glob("*.cs*")
        for path in paths:
            with suppress(OSError):
                path.unlink(missing_ok=True)

    def _consumer(self, heartbeat: int) -> tuple[RuntimeInformation, tuple[int, int]] | None:
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

        item_list: list[tuple[int, NetworkItem]] | None = []
        messages: list[tuple[int, str]] | None = []
        location_ids: set[int] | None = set()
        death_links: list[tuple[int, int, str]] | None = []
        death_ack: int | None = None
        # heartbeat and ack should remember their last values instead of
        # sending empty/null/nodata values.

        for entry in outgoing_data:
            if entry[0] == "item":
                item_list.append(entry[1])
            if entry[0] == "location":
                location_ids.add(entry[1])
            if entry[0] == "message":
                messages.append(entry[1])
            if entry[0] == "death_link":
                death_links.append(entry[1])
            if entry[0] == "death_ack":
                death_ack = entry[1]
            if entry[0] == "status":
                self.last_connection_status = entry[1]

        if len(item_list) == 0:
            item_list = None
        if len(location_ids) == 0:
            location_ids = None
        if len(messages) == 0:
            messages = None
        if len(death_links) == 0:
            death_links = None

        ri = RuntimeInformation(item_list, location_ids, None, messages, death_links, death_ack, None, False)
        rs = (self.last_connection_status, heartbeat)

        return (ri, rs)

    def _consume_incoming(self) -> None:
        tick_count = 0
        try:
            while not self.communication_closed:
                started = time.perf_counter()
                queue_values = self._consumer(tick_count)
                tick_count += 1
                if queue_values is not None:
                    try:
                        self._send_client_status_connection(queue_values[1][0])
                    except Exception:
                        logger.exception("Failed to update connection status.")
                    try:
                        self._send_client_status_heartbeat(queue_values[1][1])
                    except Exception:
                        logger.exception("Failed to update heartbeat.")
                    try:
                        self._receive_game_status_heartbeat()
                    except Exception:
                        logger.exception("Failed to receive game heartbeat.")
                    try:
                        self._receive_game_status_ack()
                    except Exception:
                        logger.exception("Failed to receive game ack.")
                    try:
                        self._receive_game_status_requirements()
                    except Exception:
                        logger.exception("Failed to receive game requirements.")
                    try:
                        self._receive_game_status_win()
                    except Exception:
                        logger.exception("Failed to receive game win.")
                    try:
                        self._receive_game_information()
                    except Exception:
                        logger.exception("Failed to receive game information.")
                    try:
                        self._send_host_information(queue_values[0])
                    except Exception:
                        logger.exception("Failed to send host information.")
                time.sleep(max(0.0, self.contract.tick_time - (time.perf_counter() - started)))
        finally:
            try:
                self._on_exit()
            finally:
                self.thread_exit.set()

    def _test_sandbox_access(self) -> None:
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

    def _is_game_alive(self) -> bool:
        return self._max_heartbeat_timeout > time.perf_counter() - self.time_since_last_heartbeat_update

    def _write_file(self, name: str, data: str, status: bool = False) -> bool:
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

    def _read_file(self, name: str, status: bool = False) -> list[str]:
        base_path = self.sandbox / name
        rd_path = self.sandbox / f"{name}.rd"
        old_data: str | None = None
        ret: list[str] = []

        if status:
            with suppress(OSError):
                raw = base_path.read_text()
                ret.append(raw)
            return ret

        if rd_path.exists():
            # Attempt to recover the stray file
            with suppress(OSError):
                old_data = rd_path.read_text()
                ret.append(old_data)
            with suppress(OSError):
                rd_path.unlink(missing_ok=True)

        if not base_path.exists():
            return ret

        try:
            base_path.rename(rd_path)
        except FileExistsError:
            # Let's attempt to recover this stray file.
            if old_data is None:
                # Otherwise we already recovered it, but unlink failed.
                with suppress(OSError):
                    old_data = rd_path.read_text()
                    ret.append(old_data)
                with suppress(OSError):
                    rd_path.unlink()

            try:
                # .rd was recovered, otherwise this wouldn't be reachable;
                # we can use replace directly here.
                os.replace(base_path, rd_path)
            except OSError:
                return ret
        except OSError:
            return ret

        try:
            data = rd_path.read_text()
        except OSError:
            # Leaves stray, hopefully caught in the next tick.
            return ret

        ret.insert(0, data)

        with suppress(OSError):
            rd_path.unlink(missing_ok=True)

        return ret

    async def _send_connection_context(self, cctx: ConnectionContext) -> None:
        message, _exit_code = self.contract.write_content("cctx", cctx.to_dict())
        # Doesn't need buffer, just resend the same data in case of error.
        attempts = 0
        while not self._write_file("ap.cctx", message):
            attempts += 1
            await asyncio.sleep(1.0)
            if attempts >= 5:  # hardcoded for now, might include in the contract later
                raise OSError("Could not write connection context.")

    async def _send_location_information(self, li: LocationInformation) -> None:
        message, _exit_code = self.contract.write_content("li", li.to_dict())
        # Doesn't need buffer, just resend the same data.
        attempts = 0
        while not self._write_file("ap.li", message):
            attempts += 1
            await asyncio.sleep(1.0)
            if attempts >= 5:
                raise OSError("Could not write location information.")

    def _send_host_information(self, hi: RuntimeInformation) -> None:
        hi = hi.merge(self.host_information_buffer, merger_first=True)
        cap = self.contract.max_messages_per_tick

        if hi.messages is not None:
            hi.messages = hi.messages[-cap:]
        self.host_information_buffer = hi

        if not (
            self.host_information_buffer.item_list or
            self.host_information_buffer.locations or
            self.host_information_buffer.messages or
            self.host_information_buffer.death_link or
            self.host_information_buffer.death_ack
        ):
            # Do not send an unnecessary empty message
            return

        message, _exit_code = self.contract.write_content("hi", self.host_information_buffer.to_dict())

        if self._write_file("ap.hi", message):
            self.host_information_buffer = None

    def _send_client_status_heartbeat(self, heartbeat: int) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        params = {
            "flag": "cshb",
            "value": heartbeat
        }

        name, _ = self.contract.write_content("cshb", params)
        new_path = self.sandbox / name

        path_list = self.sandbox.glob("*.cshb")
        sorted_paths = list(path_list)

        if len(sorted_paths) == 0:
            # create
            with suppress(OSError):
                new_path.write_text("")
        elif len(sorted_paths) == 1:
            # rename
            if new_path.exists():
                return
            file = sorted_paths[0]
            with suppress(OSError):
                file.rename(new_path)
        else:
            # delete older, rename newest
            file = sorted_paths.pop()
            for entry in sorted_paths:
                with suppress(OSError):
                    entry.unlink()
            if file == new_path:
                return
            with suppress(OSError):
                file.rename(new_path)

    def _send_client_status_connection(self, connected: int) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        params = {
            "flag": "csc",
            "value": connected
        }

        name, _ = self.contract.write_content("csc", params)
        new_path = self.sandbox / name

        path_list = self.sandbox.glob("*.csc")
        sorted_paths = list(path_list)

        if len(sorted_paths) == 0:
            # create
            with suppress(OSError):
                new_path.write_text("")
        elif len(sorted_paths) == 1:
            # rename
            if new_path.exists():
                return
            file = sorted_paths[0]
            with suppress(OSError):
                file.rename(new_path)
        else:
            # delete older, rename newest
            file = sorted_paths.pop()
            for entry in sorted_paths:
                with suppress(OSError):
                    entry.unlink()
            if file == new_path:
                return
            with suppress(OSError):
                file.rename(new_path)

    def _receive_game_information(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        raw: list[str] = self._read_file("ap.gi")
        # Could not open file, try again next tick.
        if len(raw) == 0:
            return

        game_information: dict[str, Any] = self.contract.read_content("gi", raw[0])
        message: dict[str, Any] | None = game_information.get("message")
        if message is None or not isinstance(message, dict):
            return

        locations: set[int] | None = set(l_ids) if (l_ids := message.get("location_ids")) is not None else None
        death_data: dict[str, Any] | None = message.get("death_link")
        death_link: tuple[int, int, str] | None = None
        if (
            death_data is not None and
            isinstance(death_data, dict) and
            isinstance(death_data.get("id"), int) and
            isinstance(death_data.get("message"), str)
        ):
            death_link = (-1, death_data["id"], death_data["message"])
        location_acks: set[int] | None = set(l_ids) if (l_ids := message.get("location_acks")) is not None else None
        death_ack: int | None = message.get("death_ack")
        _exit_code: int | None = game_information.get("exit_code")  # Currently does nothing
        if len(raw) > 1:
            # we can only ever have 2 entries here
            class GetOutOfHereError(Exception):
                pass
            # This here is old information
            with suppress(JSONDecodeError, GetOutOfHereError):
                game_information_: dict[str, Any] = self.contract.read_content("gi", raw[1])
                message_ = game_information_.get("message")
                if message_ is None:
                    raise GetOutOfHereError
                locations_: set[int] | None = \
                    set(l_ids) if (l_ids := message_.get("location_ids")) is not None else None
                if locations_ is not None:
                    locations = (locations or set()) | locations_
                if death_link is None:  # Prioritize the newer
                    death_data_: dict[str, Any] | None = message_.get("death_link")
                    if (
                        death_data_ is not None and
                        isinstance(death_data_, dict) and
                        isinstance(death_data_.get("id"), int) and
                        isinstance(death_data_.get("message"), str)
                    ):
                        death_link = (-1, death_data_["id"], death_data_["message"])
                location_acks_: set[int] | None = \
                    set(l_ids) if (l_ids := message_.get("location_acks")) is not None else None
                if location_acks_ is not None:
                    location_acks = (location_acks or set()) | location_acks_
                death_ack_: int | None = message_.get("death_ack")
                if death_ack_ is not None:
                    # Prioritize the newer
                    death_ack = death_ack if death_ack is not None else death_ack_
                    pass
                __exit_code: int | None = game_information_.get("exit_code")  # Currently does nothing

        if locations is not None:
            for entry in locations:
                self.gth_q.put(("location", entry))
        if death_link is not None:
            self.gth_q.put(("death_link", death_link))
        if death_ack is not None:
            self.gth_q.put(("death_ack", death_ack))
        if location_acks is not None:
            for entry in location_acks:
                self.gth_q.put(("location_ack", entry))

    def _receive_game_status_heartbeat(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown:
            return

        path_list = self.sandbox.glob("*.gshb")
        try:
            latest_file = next(path_list)
        except StopIteration:
            # No .gshb files in the sandbox folder
            return

        with suppress(StopIteration):
            next(path_list)
            # Stop iteration didn't raise, so there are multiple files.
            # Should be read as no-data
            return

        raw = self.contract.read_content("gshb", latest_file.name)

        try:
            beat = int(raw["message"])
        except ValueError:
            if latest_file not in unknown_path_set:
                unknown_path_set.add(latest_file)
                logger.warning(f"Unexpected flag name: {latest_file}")
            # Unknown value error
            return

        if beat != self.last_game_heartbeat:
            self.last_game_heartbeat = beat
            self.time_since_last_heartbeat_update = time.perf_counter()
        # No writes to the queue, since the client really doesn't need to know this

    def _receive_game_status_requirements(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown or not self._is_game_alive():
            return

        path_list = self.sandbox.glob("*.gsreq")

        try:
            latest_file = next(path_list)
        except StopIteration:
            # No .gsreq files in the sandbox folder
            return

        ambiguous = True

        try:
            next(path_list)
        except StopIteration:
            ambiguous = False

        if ambiguous:
            # Ambiguous state, treat as no-data
            return

        raw = self.contract.read_content("gsreq", latest_file.name)

        # gsreq does not require memory
        try:
            state = int(raw["message"])
        except ValueError:
            if latest_file not in unknown_path_set:
                unknown_path_set.add(latest_file)
                logger.warning(f"Unexpected flag name: {latest_file}")
            # Unknown value error
            return
        req_cctx: bool = bool(state & 0b10)
        req_li: bool = bool(state & 0b01)

        if req_cctx:
            self.gth_q.put(("req_cctx", True))
        if req_li:
            self.gth_q.put(("req_li", True))

    def _receive_game_status_ack(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown or not self._is_game_alive():
            return

        path_list = self.sandbox.glob("*.gsack")

        try:
            latest_file = next(path_list)
        except StopIteration:
            # No .gsack files in the sandbox folder
            return

        ambiguous = True

        try:
            next(path_list)
        except StopIteration:
            ambiguous = False

        if ambiguous:
            # Ambiguous state, treat as no-data
            return

        raw = self.contract.read_content("gsack", latest_file.name)

        try:
            ack = int(raw["message"])
        except ValueError:
            if latest_file not in unknown_path_set:
                unknown_path_set.add(latest_file)
                logger.warning(f"Unexpected flag name: {latest_file}")
            # Unknown value error
            return

        self.gth_q.put(("ack", ack))

    def _receive_game_status_win(self) -> None:
        if self.gth_q is None or self.gth_q.is_shutdown or not self._is_game_alive():
            return

        path_list = self.sandbox.glob("*.gswin")

        try:
            latest_file = next(path_list)
        except StopIteration:
            # No .gswin files in the sandbox folder
            return

        ambiguous = True

        try:
            next(path_list)
        except StopIteration:
            ambiguous = False

        if ambiguous:
            # Ambiguous state, treat as no-data
            return

        raw = self.contract.read_content("gswin", latest_file.name)

        try:
            win = int(raw["message"])
        except ValueError:
            if latest_file not in unknown_path_set:
                unknown_path_set.add(latest_file)
                logger.warning(f"Unexpected flag name: {latest_file}")
            # Unknown value error
            return

        self.gth_q.put(("is_win", win))
