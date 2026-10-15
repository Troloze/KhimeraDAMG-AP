from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from contextlib import suppress
from copy import deepcopy
from typing import TYPE_CHECKING, Any, ClassVar

import Utils  # type: ignore
from CommonClient import (  # type: ignore
    ClientCommandProcessor,
    ClientStatus,
    CommonContext,
    get_base_parser,
    gui_enabled,
    handle_url_arg,
    logger,
    server_loop,
)
from NetUtils import JSONMessagePart, JSONtoTextParser, NetworkItem  # type: ignore

from .. import APWORLD_VERSION, GAME_FULL_NAME
from .communication import KhimeraDAMGCommunicationInterface
from .launcher import KhimeraDAMGLauncher
from .patcher import SourceNotFoundError, source_get, try_load_build
from .storage import KhimeraDAMGStorageHandler
from .types import ConnectionContext, LocationInformation, RuntimeInformation

if TYPE_CHECKING:
    import kvui  # type: ignore


def get_game_id(slot: str, seed: str) -> str:
    return hashlib.md5(f"{slot}_{seed}".encode()).hexdigest()


class KhimeraDAMGJSONToTextParser(JSONtoTextParser):
    def _handle_color(self, node: JSONMessagePart) -> str:
        return self._handle_text(node)  # No colors for the in-game text


class KhimeraDAMGCommandProcessor(ClientCommandProcessor):
    continue_timeout: ClassVar[float] = 60.0

    def __init__(self, ctx: KhimeraDAMGContext) -> None:
        super().__init__(ctx)
        self.ctx = ctx
        self.command_running: bool = False
        self.continue_context: str | None = None
        self.continue_args: dict | None = None
        self.continue_time: float | None = None

    if (False):  # Debug commands, not available for the actual release of the apworld
        ##################
        # Debug Handlers #
        ##################

        def _cmd_force_win(self) -> None:
            """ DEBUG COMMAND.\nForces a win """
            # Deliberately doesn't check for command_running.
            self.continue_context = None
            self.continue_time = None
            self.continue_args = None
            if isinstance(self.ctx, KhimeraDAMGContext):
                Utils.async_start(self.ctx.send_msgs(
                    [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
                ))

        def _cmd_die(self) -> None:
            """ DEBUG COMMAND.\nSends a fake death link signal to the game."""
            # Deliberately doesn't check for command_running.
            self.continue_context = None
            self.continue_time = None
            self.continue_args = None
            if isinstance(self.ctx, KhimeraDAMGContext):
                if self.ctx.communication_interface is not None:
                    self.ctx.communication_interface.send_death_link("", -1, "")

    ######################
    # Game Data Handlers #
    ######################

    def _cmd_export_game_data(self, seed: str = "", slot_name: str = "") -> None:
        """
            Exports a copy of the stored game data for the currently loaded slot.
            If seed and slot_name is provided, you can export data from a non-connected slot (as long as it exists)
            Import it using import game data.

            :param seed: The seed of the hosted game.
            :param slot_name: The name of your slot. Use quotes if the name contains spaces.
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        g_id = None

        if slot_name == "" or seed == "":
            g_id = self.ctx.game_id
            if g_id is None:
                logger.info("Please provide the name and seed parameters, "
                            "or use this command while the client is connected."
                )
                return
        else:
            g_id = get_game_id(slot_name, seed)

        has_data = KhimeraDAMGStorageHandler.probe_data(g_id)
        if not has_data:
            logger.info("No data found for this slot.")
            return

        async def exporter(g_id: str, command_processor: KhimeraDAMGCommandProcessor) -> None:
            try:
                result = await KhimeraDAMGStorageHandler.save_data(g_id)
                if result:
                    logger.info("Exported game data successfully.")
                else:
                    logger.warning("Failed to export game data.")
            except Exception:
                logger.warning("Failed to export game data.")
            finally:
                command_processor.command_running = False
        self.command_running = True
        Utils.async_start(exporter(g_id, self))
        logger.info("Opening the file explorer...")

    def _cmd_import_game_data(self) -> None:
        """
            Loads and exported copy of the game data for the currently loaded slot.
            Note that this requires the exported data's slot to match the currently loaded one.

            This operation is irreversible and can cause data loss, make sure you know what you're doing.
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None

        async def importer(command_processor: KhimeraDAMGCommandProcessor) -> None:
            try:
                file_name = await asyncio.to_thread(
                    Utils.open_filename,
                    "Import game data",
                    [("Khimera DAMG data", [".kdamgdata"])]
                )
                game_id = KhimeraDAMGStorageHandler.probe_load(file_name)
                if game_id is None:
                    logger.warning("Failed to import game data.")
                    return
                if game_id == "":
                    if KhimeraDAMGStorageHandler.load_data(file_name):
                        logger.info("Imported game data successfully.")
                    else:
                        logger.warning("Failed to import game data.")
                    return
                if self.ctx.game_id is not None and self.ctx.game_id == game_id:
                    logger.warning("Cannot import data to the currently loaded slot. Close the game and try again.")
                    return

                logger.info("There already is a data file for the loaded slot; would you like to overwrite it? "
                            "This operation is irreversible"
                )
                logger.info("Send /confirm in order to import your game data.")
                command_processor.continue_context = "import"
                command_processor.continue_time = time.perf_counter()
                command_processor.continue_args = {"file_name": file_name}
            finally:
                command_processor.command_running = False
        self.command_running = True
        Utils.async_start(importer(self))

    def _cmd_reset_game_data(self, seed: str = "", slot_name: str = "") -> None:
        """
            Deletes the stored game data for a slot.
            Running this command will destroy your safe file.

            :param seed: The seed of the hosted game.
            :param slot_name: The name of your slot. Use quotes if the name contains spaces.
            This operation is irreversible and can cause data loss, make sure you know what you're doing.
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None

        if slot_name == "" or seed == "":
            logger.info("Please provide the name and seed parameters.")
            return

        g_id = get_game_id(slot_name, seed)
        if self.ctx.game_id == g_id:
            # Not exactly the correct condition to enter here, but it will work while we don't have a launcher
            logger.info("You cannot reset the currently loaded game data. Close the game and try again.")
            return

        has_data = KhimeraDAMGStorageHandler.probe_data(g_id)
        if not has_data:
            logger.info("No data found for this slot.")
            return

        # Check if the slot is connected.
        self.continue_context = "reset"
        self.continue_time = time.perf_counter()
        self.continue_args = {"g_id": g_id}
        logger.info("This operation is irreversible and can cause data loss.")
        logger.info("Send /confirm in order to reset your game data.")

    def _cmd_wipe_all_game_data(self) -> None:
        """
            Deletes all the stored game data.
            Running this command will destroy every save file, except for the currently loaded data.

            This operation is irreversible, make sure you know what you're doing.
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        g_id = self.ctx.game_id

        self.continue_context = "wipe"
        self.continue_args = {"g_id": g_id}
        self.continue_time = time.perf_counter()

        logger.info("Would you like to delete all game data? This operation is irreversible.")
        if g_id is not None:
            logger.info("Note: This will not delete the currently loaded game data.")
        logger.info("Send /confirm in order to wipe the game data.")

    #####################
    # Launcher Handlers #
    #####################

    def _cmd_launch(self) -> None:
        """
            Launches the game.
            [Requires an active connection]
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        if (
            not self.ctx._is_server_connected() or
            self.ctx.host_world_version is None or
            self.ctx.current_address is None or
            self.ctx.slot_name is None or
            self.ctx.game_id is None
        ):
            logger.warning("Failed to launch game: You can only launch a game when connected to a slot.")
            return
        if (
            self.ctx.communication_interface is None or
            not self.ctx.communication_interface.running or
            self.ctx.communication_interface.stopped
        ):
            logger.warning("Communication systems are currently not running, please reconnect to restart them.")
            return

        if self.ctx.launcher.tracking:
            logger.warning("Failed to launch game: There already is game running.")
            return

        async def launch(ctx: KhimeraDAMGContext) -> None:
            try:
                await self.ctx.launcher.launch_game(
                    ctx.host_world_version,  # type: ignore
                    ctx.current_address,  # type: ignore
                    ctx.slot_name,  # type: ignore
                    ctx.game_id  # type: ignore
                )
            except Exception as err:
                logger.warning(str(err))
            finally:
                self.command_running = False
        self.command_running = True
        Utils.async_start(launch(self.ctx))

    def _cmd_close_game(self) -> None:
        """ Closes the game. """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        if not self.ctx.launcher.tracking:
            logger.warning("The client could not detect any instance of the game running.")
            return

        async def terminate(ctx: KhimeraDAMGContext) -> None:
            try:
                await ctx.launcher.terminate()
            finally:
                self.command_running = False

        self.command_running = True
        Utils.async_start(terminate(self.ctx))

    ########
    # Misc #
    ########

    def _cmd_status(self) -> None:
        """Check Khimera DAMG Connection State"""
        # Deliberately doesn't check for command_running.
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        if isinstance(self.ctx, KhimeraDAMGContext):
            logger.info(self.ctx.get_khimera_damg_status())

    def _cmd_connection_info(self) -> None:
        """ Prints connection information """
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        if isinstance(self.ctx, KhimeraDAMGContext):
            logger.info(
                f"Slot name: {self.ctx.slot_name}\n"
                f"Address:   {self.ctx.current_address}\n"
                f"Seed:      {self.ctx.host_seed}"
            )

    def _cmd_confirm(self) -> None:
        """
            Confirmation command, does nothing on its own.
            Once a dangerous command is issued, you will be asked to use this.
        """
        def confirm() -> bool:
            if self.continue_context == "wipe":
                self.continue_context = "wipe_"
                self.continue_time = time.perf_counter()
                has_gid = None
                if self.continue_args is not None:
                    has_gid = self.continue_args.get("g_id")
                logger.info("This will delete all *archipelago related* "
                            "Khimera: Destroy All Monster Girls game data file in your machine. "
                            "Are you absolutely sure this is what you want to do?")
                if has_gid:
                    logger.info("Note: This will not delete the currently loaded game data.")
                logger.info("Send /confirm again in order to wipe the game data. (LAST WARNING)")
                return True
            if self.continue_context == "wipe_":
                # Wipe everything.
                g_id = None if self.continue_args is None else self.continue_args.get("g_id")
                KhimeraDAMGStorageHandler.wipe(g_id)
                if g_id is None:
                    logger.info("All game data has been deleted.")
                else:
                    logger.info("All game data (except the currently loaded) has been deleted.")
            elif self.continue_context == "reset":
                if self.continue_args is None or "g_id" not in self.continue_args:
                    logger.warning("Error: Attempt to execute a reset action without defining import arguments "
                                "(This is the dev's fault, please notify them)"
                    )
                    return False
                g_id = self.continue_args["g_id"]
                if KhimeraDAMGStorageHandler.delete_data(g_id):
                    logger.info("Deleted game data successfully.")
                else:
                    logger.warning("Failed to delete game data.")
                self.continue_context = None
                self.continue_time = None
                self.continue_args = None
            elif self.continue_context == "import":
                if self.continue_args is None or "file_name" not in self.continue_args:
                    logger.warning("Error: Attempt to execute an import action without defining import arguments "
                                "(This is the dev's fault, please notify them)"
                    )
                    return False
                file_name = self.continue_args["file_name"]
                if KhimeraDAMGStorageHandler.load_data(file_name):
                    logger.info("Imported game data successfully.")
                else:
                    logger.warning("Failed to import game data.")
            return False

        if self.command_running:
            logger.warning("Theres a command being currently executed.")
        elif self.continue_context is None or self.continue_time is None:
            logger.info("Nothing to confirm.")
        elif self.continue_time < time.perf_counter() - self.continue_timeout:
            logger.info("You took too long to confirm, please try again.")
            self.continue_context = None
            self.continue_time = None
            self.continue_args = None
        else:
            pending = False
            try:
                pending = confirm()
            finally:
                if not pending:
                    self.continue_context = None
                    self.continue_time = None
                    self.continue_args = None


class KhimeraDAMGConnectionState:
    def __init__(self, ctx: KhimeraDAMGContext) -> None:
        self.context: KhimeraDAMGContext = ctx
        self.lock: threading.Lock = threading.Lock()
        self.game_last_deathlink: tuple[str, int, str] | None = None
        self.gdl_ack: set[int] = set()
        self.pending_gdl_ack: int | None = None
        self.host_last_deathlink: tuple[str, int, str] | None = None
        self.locations_acked: set[int] = set()
        self.hdl_id: int = 0
        self._goal_status_ready: asyncio.Event | None = None
        self.pending_acked_data: set[int] | None = None
        self.last_ack: int = 0
        self.req_cctx: bool | None = None
        self.req_li: bool | None = None

    def reset(self) -> None:
        with self.lock:
            self.game_last_deathlink = None
            self.gdl_ack = set()
            self.pending_gdl_ack = None
            self.host_last_deathlink = None
            self.locations_acked = set()
            self.hdl_id = 0
            self._goal_status_ready = None
            self.pending_acked_data = None
            self.last_ack = 0
            self.req_cctx = None
            self.req_li = None

    def get_game_deathlink(self) -> tuple[str, int, str] | None:
        with self.lock:
            return self.game_last_deathlink

    def get_game_deathlink_ack(self) -> int | None:
        with self.lock:
            pending = self.pending_gdl_ack
            self.pending_gdl_ack = None
            return pending

    def set_game_deathlink(self, dl: tuple[str, int, str] | None) -> None:
        with self.lock:
            if dl is None:
                return
            if dl[1] not in self.gdl_ack:
                self.game_last_deathlink = dl
            else:
                self.pending_gdl_ack = dl[1]

    def set_game_deathlink_ack(self, dl_id: int) -> None:
        with self.lock:
            self.gdl_ack.add(dl_id)
            if self.pending_gdl_ack is not None and self.pending_gdl_ack == dl_id:
                self.pending_gdl_ack = None
            if self.game_last_deathlink is None:
                return
            if self.game_last_deathlink[1] == dl_id:
                self.game_last_deathlink = None

    def get_host_deathlink(self) -> tuple[str, int, str] | None:
        with self.lock:
            return self.host_last_deathlink

    def set_host_deathlink(self, sender: str, message: str) -> None:
        with self.lock:
            self.hdl_id += 1
            self.host_last_deathlink = (sender, self.hdl_id, message)

    def set_host_deathlink_ack(self, dl_id: int) -> None:
        with self.lock:
            if self.host_last_deathlink is None:
                return
            if self.host_last_deathlink[1] == dl_id:
                self.host_last_deathlink = None

    def set_location_acked(self, location_id: int | set[int]) -> None:
        with self.lock:
            if isinstance(location_id, int):
                self.locations_acked.add(location_id)
            elif isinstance(location_id, set):
                self.locations_acked |= location_id

    def get_unacked_locations(self) -> set[int]:
        l_acked: set[int]
        with self.lock:
            l_acked = self.locations_acked.copy()
        l_checked = self.context.checked_locations
        return l_checked - l_acked

    def set_item_ack(self, ack: int) -> None:
        with self.lock:
            if ack > self.last_ack:
                self.last_ack = ack

    def get_last_ack(self) -> int:
        with self.lock:
            return self.last_ack

    def get_unacked_items(self) -> list[tuple[int, NetworkItem]]:
        ack: int
        with self.lock:
            ack = self.last_ack
        item_list = self.context.items_received
        return [(i + 1, item_list[i]) for i in range(ack, len(item_list))]

    def set_data(self, data: list[tuple[int, str, Any]]) -> None:
        if self.context.game_id is None:
            return
        keys = [entry[1] for entry in data]
        values = [entry[2] for entry in data]
        try:
            KhimeraDAMGStorageHandler.store_many(keys, values, self.context.game_id, "game_data", folder="game_data")
        except OSError:
            # Don't ack, don't signal, the game will send it again later.
            return
        with self.lock:
            self.pending_acked_data = (self.pending_acked_data or set()) | {entry[0] for entry in data}

    def get_pending_data_ack(self) -> list[int] | None:
        with self.lock:
            pending = self.pending_acked_data
            self.pending_acked_data = None
            return list(pending) if pending is not None else None

    def set_req_cctx(self) -> None:
        self.req_cctx = True

    def set_req_li(self) -> None:
        self.req_li = True

    def get_req_cctx(self) -> bool | None:
        ret = self.req_cctx
        self.req_cctx = None
        return ret

    def get_req_li(self) -> bool | None:
        ret = self.req_li
        self.req_li = None
        return ret


class KhimeraDAMGContext(CommonContext):
    command_processor = KhimeraDAMGCommandProcessor
    game = GAME_FULL_NAME
    items_handling = 0b111

    class FailedToStartCommunicationError(Exception):
        pass

    def __init__(self, server_address: str | None = None, password: str | None = None) -> None:
        super().__init__(server_address, password)
        self.launcher: KhimeraDAMGLauncher = KhimeraDAMGLauncher(ctx=self)
        self.slot_data: dict[str, Any] = {}
        self.communication_interface: KhimeraDAMGCommunicationInterface | None = None
        self.interface_start = None
        self.interface_stop = None
        self.is_game_connected = False
        self.slot_data_empty_once: bool = False
        self.communication_task: asyncio.Task | None = None
        self.communication_stop_event: asyncio.Event | None = None
        self.communication_cooldown: float = 0.05
        self.connection_state: KhimeraDAMGConnectionState = KhimeraDAMGConnectionState(self)
        self.json_to_text = KhimeraDAMGJSONToTextParser(self)
        self.slot_name: str | None = None
        self.host_seed: str | None = None
        self.current_address: str | None = None
        self.game_id: str | None = None
        self.host_world_version: str | None = None
        self.cctx: ConnectionContext | None = None
        self.li: LocationInformation | None = None
        self._connection_task: asyncio.Task | None = None
        self._connection_gui_bypass: bool = False
        self._kvui_started: bool = False

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)

        await self.get_username()
        await self.send_connect()

    async def send_death(self, death_text: str = "") -> None:
        if not self._is_server_connected():
            return None
        return await super().send_death(death_text)

    async def _process_game_package(self, game_package: RuntimeInformation | None) -> None:
        if game_package is None:
            return

        if game_package.locations is not None:
            self.locations_checked |= game_package.locations & self.server_locations
            await self.check_locations(game_package.locations)

        if game_package.location_acks is not None:
            self.connection_state.set_location_acked(game_package.location_acks)

        if game_package.death_link is not None:
            self.connection_state.set_game_deathlink(game_package.death_link)

        if game_package.death_ack is not None:
            self.connection_state.set_host_deathlink_ack(game_package.death_ack)

        if game_package.data is not None:
            self.connection_state.set_data(game_package.data)

        if game_package.ack is not None:
            last_ack = self.connection_state.get_last_ack()
            self.connection_state.set_item_ack(game_package.ack)
            if game_package.ack > last_ack:
                if self.game_id is not None:
                    KhimeraDAMGStorageHandler.store("last_ack", game_package.ack, self.game_id, folder="game_data")

        if game_package.req_cctx is not None:
            self.cctx = self._make_cctx()
            self.connection_state.set_req_cctx()

        if game_package.req_li is not None:
            self.connection_state.set_req_li()

        # Checks for both None and False
        if game_package.is_win and not self.finished_game:
            self.finished_game = True
            await self.send_msgs(
                [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
            )

    async def _process_connection_state(self) -> None:
        gdlink = self.connection_state.get_game_deathlink()
        if gdlink is not None and self._is_server_connected():
            await self.send_death(gdlink[2])
            self.connection_state.set_game_deathlink_ack(gdlink[1])
            if self.communication_interface is not None:
                self.communication_interface.send_death_ack(gdlink[1])

        gdlink_ack = self.connection_state.get_game_deathlink_ack()
        if gdlink_ack is not None and self.communication_interface is not None:
            self.communication_interface.send_death_ack(gdlink_ack)

        hdlink = self.connection_state.get_host_deathlink()
        if hdlink is not None and self.communication_interface is not None:
            self.communication_interface.send_death_link(
                hdlink[0],
                hdlink[1],
                hdlink[2]
            )

        items = self.connection_state.get_unacked_items()
        if items is not None and self.communication_interface is not None:
            self.communication_interface.send_items(items)

        locations = self.connection_state.get_unacked_locations()
        if locations is not None and self.communication_interface is not None:
            self.communication_interface.send_locations(locations)

        data_ack = self.connection_state.get_pending_data_ack()
        if data_ack is not None and self.communication_interface is not None:
            self.communication_interface.send_data_acks(data_ack)

        req_cctx = self.connection_state.get_req_cctx()
        if req_cctx is not None and self.communication_interface is not None:
            self.communication_interface.send_connection_context(self.cctx)  # type: ignore

        req_li = self.connection_state.get_req_li()
        if req_li is not None and self.communication_interface is not None:
            self.communication_interface.send_location_information(self.li)  # type: ignore

    async def _communication_loop(self) -> None:
        if self.host_world_version is None:
            logger.exception("Attempt to start the server loop without an active connection")
            return
        if self.communication_interface is None:
            logger.exception("Attempt to start the server loop without instancing the communication interface")
            return
        if self.cctx is None:
            logger.exception("Attempt to start the server loop without creating the connection context")
            return
        if self.li is None:
            logger.exception("Attempt to start the server loop without creating the location information")
            return
        p_e = None
        p_et = 0.0
        p_ec = 1.0
        # Only sends things UP to the host
        self.communication_stop_event = asyncio.Event()
        game_status = None
        while not self.communication_stop_event.is_set():
            start = time.perf_counter()
            # ruff: disable[too-many-statements-in-try-clause]
            try:
                if self.communication_interface is None or not self.communication_interface.running:
                    continue
                # Heartbeat probe
                if game_status is None:
                    game_status = asyncio.create_task(
                        self.communication_interface.probe_game_status(self.host_world_version),
                        name="kdamg_client_probe_heartbeat"
                    )
                elif game_status.done():
                    self.is_game_connected = await game_status
                    game_status = None

                # Host connection probe
                self.communication_interface.send_connection_status(self._is_server_connected())

                game_package = self.communication_interface.consume_outgoing()
                # Handles information sent by the game
                await self._process_game_package(game_package)
                # Dispatches packages to host and game based on connection state
                await self._process_connection_state()
            except Exception as err:
                if not (
                    p_e is not None and
                    p_e[0] is type(err) and p_e[1] == str(err) and
                    time.perf_counter() - p_et < p_ec
                ):
                    logger.exception(f"An exception was raised in server loop: {err}")
                    p_et = time.perf_counter()
                p_e = (type(err), str(err))
            finally:
                await asyncio.sleep(max(0.0, self.communication_cooldown - (time.perf_counter() - start)))
            # ruff: enable[too-many-statements-in-try-clause]
        self.communication_stop_event = None

    async def _close_communication(self) -> None:
        if self.communication_interface is not None:
            await self.communication_interface.stop()
            self.communication_interface = None
        if self.communication_stop_event is not None:
            self.communication_stop_event.set()
        if self.communication_task is not None:
            await self.communication_task
            self.communication_task = None

    def _make_cctx(self) -> ConnectionContext:
        last_ack = max(
            self.connection_state.get_last_ack(),
            KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0, folder="game_data")  # type: ignore
        )

        if self.slot_name is None or self.host_world_version is None or self.game_id is None:
            if self.cctx is not None:
                game_data = KhimeraDAMGStorageHandler.get("game_data", self.cctx.game_id, {}, folder="game_data")  # type: ignore
                return ConnectionContext(
                    ap_version=self.cctx.ap_version,
                    host_world_version=self.cctx.host_world_version,
                    client_world_version=self.cctx.client_world_version,
                    slot_name=self.cctx.slot_name,
                    seed=self.cctx.seed,
                    last_ack=last_ack,
                    options=self.cctx.options,
                    generation_information=self.cctx.generation_information,
                    game_data=game_data,
                    locations=self.cctx.locations,
                    item_list=self.cctx.item_list,
                    has_goaled=self.cctx.has_goaled
                )
            raise RuntimeError("Attempt to make a connection context before the first server connection.")

        items = self.items_received  # Accessed asynchronously, state can change between a loop's readings
        item_list = [(i + 1, items[i]) for i in range(0, len(items))]
        win_status = self.stored_data.get(f"_read_client_status_{self.team}_{self.slot}")
        # Resolves to "False" if win_status is None
        is_win = win_status == ClientStatus.CLIENT_GOAL
        # This will return the entirety of the "game_data" category.
        game_data = KhimeraDAMGStorageHandler.get("game_data", self.game_id, {}, folder="game_data")
        return ConnectionContext(
            ap_version=Utils.__version__,
            host_world_version=self.host_world_version,
            client_world_version=APWORLD_VERSION,
            slot_name=self.slot_name,
            seed=self.host_seed,  # type: ignore
            last_ack=last_ack,
            options=self.slot_data["options"],
            generation_information=self.slot_data["generation_information"],
            game_data=game_data,
            locations=self.checked_locations,
            item_list=item_list,
            has_goaled=is_win
        )

    async def _start_up_game_processes(self) -> None:
        last_ack = KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0, folder="game_data")  # type: ignore
        self.cctx = self._make_cctx()
        self.li = LocationInformation(
            not self.slot_data["is_race"],
            self.slot_data["location_information"]
        )
        self.connection_state.set_item_ack(last_ack)

        # Shut previous interface down before starting a new one
        if self.communication_interface is not None:
            await self.communication_interface.stop()

        self.communication_interface = KhimeraDAMGCommunicationInterface()
        try:
            await self.communication_interface.start(self.cctx, self.li)
        except OSError as err:
            # Not caught as the new type, but useful to differentiate between the storage OSErrors when debugging.
            raise self.FailedToStartCommunicationError(f"Could not start communication: {err}") from err

    async def _delayed_startup(self) -> bool:
        if self.slot is None or self.host_seed is None:
            # Nothing connected, we need something connected.
            return False
        if self.host_world_version is None or self.slot_name is None:
            return False

        if (
            self.communication_interface is not None and
            not self.communication_interface.authenticate(self.slot_name, self.host_seed)
        ):
            # Different seed/slot, requires restarting communication
            # Connection state is reset by launcher, so no need to do it here.
            await self.communication_interface.stop()
            self.communication_interface = None

        # Wait for win status
        try:
            await asyncio.wait_for(self._goal_status_ready.wait(), timeout=1.0)
        except TimeoutError:
            logger.warning("Server took too long to send win information, starting anyways.")

        # Start
        if self.communication_interface is None:
            try:
                await self._start_up_game_processes()
            except Exception as err:
                self.communication_interface = None
                logger.exception(
                    f"Khimera setup failed: {err}.\nServer connection remains active, "
                    "reconnect if you intend to launch the game."
                )
                return False

        if self.communication_task is not None and self.communication_task.done():
            with suppress(Exception):
                # At this point, it doesn't matter
                await self.communication_task
            self.communication_task = None
        if self.communication_task is None:
            self.communication_task = asyncio.create_task(
                self._communication_loop(),
                name="kdamg_client_communication_loop"
            )

        # Launch game after the communication interface successfully builds!
        if not self.launcher.tracking:
            try:
                await self.launcher.launch_game(
                    self.host_world_version,
                    self.current_address,  # type: ignore
                    self.slot_name,
                    self.game_id  # type: ignore
                )
            except Exception:
                logger.exception("Khimera launch failed; server connection remains active.")
                return False

        return True

    async def _validate_connection(self) -> bool:
        if self.slot is None or self.host_seed is None or self.current_address is None:
            msg = self.launcher._message(
                "Failed to connect",
                "Unknown Common Client error.\nPlease try again later.",
                error=True
            )
            logger.warning(
                "Unknown Common Client error.\nPlease try again later.",
            )
            if msg is not None:
                msg.open()
            return False
        game = self.slot_info[self.slot].game
        if game != GAME_FULL_NAME:
            msg = self.launcher._message(
                "Failed to connect",
                f"There was an attempt to connect to an unrecognized game: \"{game}\".\n"
                "This client should only be used for \"Khimera: Destroy All Monster Girls\".",
                error=True
            )
            logger.warning(
                f"There was an attempt to connect to an unrecognized game: \"{game}\".\n"
                "This client should only be used for \"Khimera: Destroy All Monster Girls\"."
            )
            if msg is not None:
                msg.open()
            return False
        self.slot_name = self.slot_info[self.slot].name
        self.game_id = get_game_id(self.slot_name, self.host_seed)  # type: ignore
        self.host_world_version = self.slot_data["apworld_version"]

        if self.launcher.tracking:
            if APWORLD_VERSION != self.launcher.apw_version:
                msg = self.launcher._message(
                    "Version mismatch.",
                    "There was an attempt to connect while a game launched on a different version "
                    "of the apworld is running.\n"
                    "Please close the game before attempting to connect.",
                    error=True
                )
                logger.warning(
                    "There was an attempt to connect while a game launched on a different version "
                    "of the apworld is running.\n"
                    "Please close the game before attempting to connect."
                )
                if msg is not None:
                    msg.open()
                return False

            # Validation only looks at game_id
            if self.game_id != self.launcher.game_id:

                msg = self.launcher._message(
                    "Failed to connect",
                    "There was an attempt to connect to a different slot while the game is open.\n"
                    "Please close the game before switching slots.",
                    error=True
                )
                logger.warning(
                    "There was an attempt to connect to a different slot while the game is open.\n"
                    "Please close the game before switching slots."
                )
                if msg is not None:
                    msg.open()
                return False
        return True

    async def _get_slot_data(self, args: dict) -> bool:
        self.slot_data = args.get("slot_data", {})
        if len(self.slot_data) == 0:
            logger.warning("\"slot_data\" is empty, closing the connection.")
            if not self.slot_data_empty_once:
                self.slot_data_empty_once = True
                await self.disconnect(True)
            else:
                await self.disconnect(False)
            return False
        return True

    async def _on_connected(self, args: dict) -> None:
        self.current_address = self.server_address
        # Get slot data
        if not await self._get_slot_data(args):
            return
        self.slot_data_empty_once = False

        if not await self._validate_connection():
            await self.disconnect()
            return
        # Ask the host to notify the client if the game has goaled
        self.set_notify(f"_read_client_status_{self.team}_{self.slot}")
        # Goal status event that triggers when the server provides the goal status.
        self._goal_status_ready = asyncio.Event()

        if self.slot_data["options"]["death_link"]:
            # Set death link up if enabled.
            Utils.async_start(self.update_death_link(True))
        else:
            # Disable death link if not enabled.
            Utils.async_start(self.update_death_link(False))
        # Start launcher and communication handler.
        await self._delayed_startup()

    def on_package(self, cmd: str, args: dict) -> None:
        super().on_package(cmd, args)
        if cmd == "RoomInfo":
            self.host_seed = args.get("seed_name")
        elif cmd == "Connected":
            self._connection_task = asyncio.create_task(
                self._on_connected(args),
                name="kdamg_client_connection_routine"
            )
        elif cmd == "Retrieved":
            # Is slot cleared
            if (
                self._goal_status_ready is not None and
                f"_read_client_status_{self.team}_{self.slot}" in self.stored_data
            ):
                self._goal_status_ready.set()

    def on_print_json(self, args: dict) -> None:
        # Handle messages from the host
        text = self.json_to_text(deepcopy(args["data"]))
        if self.communication_interface is not None:
            self.communication_interface.send_message(args.get("slot", 0), text)
        return super().on_print_json(args)

    def on_deathlink(self, data: dict[str, Any]) -> None:
        source = data["source"]
        message = data.get("cause", "")
        self.connection_state.set_host_deathlink(source, message)
        return super().on_deathlink(data)

    async def connect(self, address: str | None = None) -> None:
        if not self._kvui_started:
            self._connection_gui_bypass = True
            if self.launcher.tracking:
                logger.warning(
                    "A game process from a previous session has been detected. "
                    f"The client was configured to automatically connect to {address}; "
                    "if the slot connected to is not the as the slot used when launching the game, "
                    "you will not be able to connect. "
                    "If this is the case, please close the game and try again; "
                    "disregard this message otherwise."
                )
        return await super().connect(address)

    async def disconnect(self, allow_autoreconnect: bool = False) -> None:
        await super().disconnect(allow_autoreconnect)

    def reset_connection_state(self) -> None:
        self.connection_state.reset()
        last_ack = KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0, folder="game_data")  # type: ignore
        self.connection_state.set_item_ack(last_ack)

    async def connection_closed(self) -> None:
        with suppress(OSError):
            self.cctx = self._make_cctx()

        self.game_id = None
        self.is_game_connected = False
        self.host_world_version = None
        self.slot_name = None
        await super().connection_closed()

    def _is_socket_open(self) -> bool:
        return self.server is not None and not self.server.socket.closed

    def _is_server_connected(self) -> bool:
        return self._is_socket_open() and self.slot is not None

    def get_khimera_damg_status(self) -> str:
        return (f"Server connected: {self._is_server_connected()},"
            f"\nGame connected: {self.is_game_connected},"
            f"\nSlot data: {self.slot_data}")

    async def detect_continued_game(self) -> None:
        if self.launcher.tracking:
            if APWORLD_VERSION != self.launcher.apw_version:
                msg = self.launcher._message(
                    "Version mismatch.",
                    "A game running from a previous session has been detected. "
                    "However, its version does not match the current apworld's version.\n"
                    "Please close the game before attempting to connect.",
                    error=True
                )
                logger.warning(
                    "A game running from a previous session has been detected. "
                    "However, its version does not match the current apworld's version.\n"
                    "Please close the game before attempting to connect."
                )
                if msg is not None:
                    msg.open()
                return

            actions = (
                "Reconnect",
                "Dismiss",
            )
            action = await self.launcher._prompt(
                "Game still running",
                "A running instance of the game from last session has been detected, "
                "would you like to reconnect to its slot?\n"
                "Note: You won't be able to connect to another slot while the game is open."
                ,
                actions
            )

            if action == actions[0]:
                self.auth = self.launcher.slot_name
                await self.connect(self.launcher.address)
        return

    async def on_kvui_start(self) -> None:
        if self._connection_gui_bypass:
            return
        # Continued game run detection
        await self.detect_continued_game()

        if self.launcher.tracking:
            # A game is already being tracked so no need to continue.
            return

        # Startup prompt
        if source_get(APWORLD_VERSION, return_any=True):
            # There's at least one source compatible with this world.
            return
        path = await self.launcher.startup_prompt()
        if path is None:
            return

        try:
            try_load_build(path)
        except (OSError, SourceNotFoundError) as err2:
            msg = self.launcher._message("Couldn't load build", "Please try again later.", error=True)
            if msg is not None:
                msg.open()
            raise err2

    def make_gui(self) -> type[kvui.GameManager]:
        import kvui  # type: ignore

        class KhimeraDAMGManager(kvui.GameManager):
            base_title = "Archipelago — Khimera: Destroy All Monster Girls Client"

            def on_start(self) -> None:
                super().on_start()
                self.ctx._kvui_started = True  # type: ignore
                Utils.async_start(self.ctx.on_kvui_start())  # type: ignore

        return KhimeraDAMGManager

    async def shutdown(self) -> None:
        await self._close_communication()

        return await super().shutdown()


def launch(*args: str) -> None:
    async def main() -> None:
        parser = get_base_parser(description="Khimera: Destroy All Monster Girls Client")
        parser.add_argument("--name", default=None, help="Slot name to connect as.")
        parser.add_argument("url", nargs="?", help="Archipelago connection url")

        parsed_args = handle_url_arg(parser.parse_args(args))

        ctx = KhimeraDAMGContext(parsed_args.connect, parsed_args.password)
        ctx.auth = parsed_args.name
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="kdamg_client_server_loop")
        if gui_enabled:
            ctx.run_gui()
            ctx.run_cli()
        else:
            ctx.run_cli()
            await ctx.detect_continued_game()

        try:
            await ctx.exit_event.wait()
        finally:
            # "finally" runs after a Ctrl + C call.
            await ctx.shutdown()

    Utils.init_logging("KhimeraDAMGClient", exception_logger="Client")

    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
