from __future__ import annotations

import asyncio
import threading
import time
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

from . import APWORLD_VERSION
from .communication import KhimeraDAMGCommunicationInterface
from .launcher import KhimeraDAMGLauncher
from .storage import KhimeraDAMGStorageHandler
from .types import ConnectionContext, LocationInformation, RuntimeInformation

if TYPE_CHECKING:
    import kvui  # type: ignore


def get_game_id(slot: str, seed: str) -> str:
    return Utils.get_file_safe_name(f"{slot}_{seed}")


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

    def _cmd_status(self) -> None:
        """Check Khimera DAMG Connection State"""
        # Deliberately doesn't check for command_running.
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        if isinstance(self.ctx, KhimeraDAMGContext):
            logger.info(self.ctx.get_khimera_damg_status())

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
                logger.info("Please provide the name and seed parameters,"
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
        Utils.async_start(exporter(g_id, self))
        self.command_running = True
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

            logger.info("There already is a data file for the loaded slot; would you like to overwrite it?"
                        "This operation is irreversible"
            )
            logger.info("Send /confirm in order to import your game data.")
            command_processor.continue_context = "import"
            command_processor.continue_time = time.perf_counter()
            command_processor.continue_args = {"file_name": file_name}
            command_processor.command_running = False

        Utils.async_start(importer(self))
        self.command_running = True

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

    def _cmd_launch(self) -> None:
        """ WIP """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        pass

    def _cmd_close_game(self) -> None:
        """ WIP """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        self.continue_context = None
        self.continue_time = None
        self.continue_args = None
        pass

    def _cmd_confirm(self) -> None:
        """
            Confirmation command, does nothing on its own.
            Once a dangerous command is issued, you will be asked to use this.
        """
        if self.command_running:
            logger.warning("Theres a command being currently executed.")
            return
        if self.continue_context is None or self.continue_time is None:
            logger.info("Nothing to confirm.")
            return
        if self.continue_time < time.perf_counter() - self.continue_timeout:
            logger.info("You took too long to confirm, please try again.")
            self.continue_time = None
            self.continue_context = None
            self.continue_args = None
            return
        if self.continue_context == "wipe":
            self.continue_context = "wipe_"
            self.continue_time = time.perf_counter()
            has_gid = None
            if self.continue_args is not None:
                has_gid = self.continue_args.get("g_id")
            logger.info("This will delete all *archipelago related*"
                        "Khimera: Destroy All Monster Girls game data file in your machine."
                        " Are you absolutely sure this is what you want to do?")
            if has_gid:
                logger.info("Note: This will not delete the currently loaded game data.")
            logger.info("Send /confirm again in order to wipe the game data. (LAST WARNING)")
            return
        if self.continue_context == "wipe_":
            # Wipe everything.
            g_id = None if self.continue_args is None else self.continue_args.get("g_id")
            KhimeraDAMGStorageHandler.wipe(g_id)
            if g_id is None:
                logger.info("All game data has been deleted.")
            else:
                logger.info("All game data (except the currently loaded) has been deleted.")
            self.continue_context = None
            self.continue_time = None
            self.continue_args = None
            return
        if self.continue_context == "reset":
            if self.continue_args is None or "g_id" not in self.continue_args:
                logger.warning("Error: Attempt to execute a reset action without defining import arguments"
                               "(This is the dev's fault, please notify them)"
                )
                return
            g_id = self.continue_args["g_id"]
            if KhimeraDAMGStorageHandler.delete_data(g_id):
                logger.info("Deleted game data successfully.")
            else:
                logger.warning("Failed to delete game data.")
            self.continue_context = None
            self.continue_time = None
            self.continue_args = None
            return
        if self.continue_context == "import":
            if self.continue_args is None or "file_name" not in self.continue_args:
                logger.warning("Error: Attempt to execute an import action without defining import arguments"
                               "(This is the dev's fault, please notify them)"
                )
                return
            file_name = self.continue_args["file_name"]
            if KhimeraDAMGStorageHandler.load_data(file_name):
                logger.info("Imported game data successfully.")
            else:
                logger.warning("Failed to import game data.")
            self.continue_time = None
            self.continue_context = None
            self.continue_args = None
            return


class KhimeraDAMGConnectionState:
    def __init__(self, ctx: KhimeraDAMGContext) -> None:
        self.context = ctx
        self.lock: threading.Lock = threading.Lock()
        self.game_last_deathlink: tuple[str, int, str] | None = None
        self.gdl_ack: set[int] = set()
        self.pending_gdl_ack: int | None = None
        self.host_last_deathlink: tuple[str, int, str] | None = None
        self.locations_acked: set[int] = set()
        self.hdl_id = 0
        self._goal_status_ready: asyncio.Event | None = None
        self.pending_acked_data: set[int] | None = None
        self.last_ack = 0

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
            KhimeraDAMGStorageHandler.store_many(keys, values, self.context.game_id, "game_data")
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


class KhimeraDAMGContext(CommonContext):
    command_processor = KhimeraDAMGCommandProcessor
    game = "Khimera: Destroy All Monster Girls"
    items_handling = 0b111

    def __init__(self, server_address: str | None = None, password: str | None = None) -> None:
        super().__init__(server_address, password)
        self.launcher: KhimeraDAMGLauncher = KhimeraDAMGLauncher()
        self.slot_data: dict[str, Any] = {}
        self.communication_interface: KhimeraDAMGCommunicationInterface | None = None
        self.interface_start = None
        self.interface_stop = None
        self.is_game_connected = False
        self.slot_data_empty_once: bool = False
        self.server_loop_task: asyncio.Task | None = None
        self.server_loop_stop_event: asyncio.Event | None = None
        self.server_loop_cooldown: float = 0.05
        self.connection_state: KhimeraDAMGConnectionState = KhimeraDAMGConnectionState(self)
        self.json_to_text = KhimeraDAMGJSONToTextParser(self)
        self.slot_name: str | None = None
        self.host_seed: str | None = None
        self.game_id: str | None = None
        self.host_world_version: str | None = None
        self.cctx: ConnectionContext | None = None
        self.li: LocationInformation | None = None

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
                    KhimeraDAMGStorageHandler.store("last_ack", last_ack, self.game_id)

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

    async def _server_loop(self) -> None:
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

        # Only sends things UP to the host
        self.server_loop_stop_event = asyncio.Event()
        game_status = None
        while not self.server_loop_stop_event.is_set():
            start = time.perf_counter()
            # ruff: disable[PLW0717]
            try:
                # Heartbeat probe
                if game_status is None:
                    game_status = asyncio.create_task(
                        self.communication_interface.probe_game_status(self.host_world_version)
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
                logger.exception(f"An exception was raised in server loop: {err}")
            await asyncio.sleep(max(0.0, self.server_loop_cooldown - (time.perf_counter() - start)))
            # ruff: enable[PLW0717]
        self.server_loop_stop_event = None

    def _get_slot_data(self, args: dict) -> bool:
        self.slot_data = args.get("slot_data", {})
        if len(self.slot_data) == 0:
            logger.warning('"slot_data" is empty, closing the connection.')
            if not self.slot_data_empty_once:
                self.slot_data_empty_once = True
                Utils.async_start(self.disconnect(True))
            else:
                Utils.async_start(self.disconnect(False))
            return False
        return True

    def _make_cctx(self) -> ConnectionContext:
        last_ack = KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0)  # type: ignore
        items = self.items_received  # Accessed asynchronously, state can change between a loop's readings
        item_list = [(i + 1, items[i]) for i in range(0, len(items))]
        win_status = self.stored_data.get(f"_read_client_status_{self.team}_{self.slot}")
        # Resolves to "False" if win_status is None
        is_win = win_status == ClientStatus.CLIENT_GOAL
        # This will return the entirety of the "game_data" category.
        game_data = KhimeraDAMGStorageHandler.get("game_data", self.game_id, {})  # type: ignore
        return ConnectionContext(
            ap_version=Utils.__version__,
            host_world_version=self.host_world_version,  # type: ignore
            client_world_version=APWORLD_VERSION,
            slot_name=self.slot_name,  # type: ignore
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
        last_ack = KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0)  # type: ignore
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
        await self.communication_interface.start(self.cctx, self.li)

    async def _delayed_startup(self) -> None:
        if self.slot is None or self.host_seed is None:
            # Nothing connected, we need something connected.
            return
        self.slot_name = self.slot_info[self.slot].name
        self.host_world_version = self.slot_data["apworld_version"]
        if self.host_world_version is None or self.slot_name is None:
            return

        self.game_id = get_game_id(self.slot_name, self.host_seed)

        if (
            self.communication_interface is not None and
            not self.communication_interface.authenticate(self.slot_name, self.host_seed)
        ):
            # Different seed/slot, requires restarting everything
            await self.communication_interface.stop()
            self.communication_interface = None
            self.connection_state.reset()

            # Insert game quitting logic
            # If game is open open a popup prompting the user for confirmation

        # Launch game first!
        if not self.launcher.is_game_running:
            if self.launcher.stored_data_validated:
                # Prompt user for permission to launch game
                try:
                    self.launcher.launch_game(self.host_world_version)  # type: ignore
                except Exception:
                    logger.exception("Khimera launch failed; server connection remains active.")

        # Wait for win status
        try:
            await asyncio.wait_for(self._goal_status_ready.wait(), timeout=1.0)
        except TimeoutError:
            logger.warning("Server took too long to send win information, starting anyways.")

        # Start
        if self.communication_interface is None:
            try:
                await self._start_up_game_processes()
            except Exception:
                logger.exception("Khimera setup failed; server connection remains active.")
        else:
            self.communication_interface.reconnect(self._make_cctx())

        if self.server_loop_task is None:
            self.server_loop_task = asyncio.create_task(self._server_loop())

    def on_package(self, cmd: str, args: dict) -> None:
        super().on_package(cmd, args)
        if cmd == "RoomInfo":
            self.host_seed = args.get("seed_name")
        elif cmd == "Connected":
            # Ask the host to notify the client if the game has goaled
            self.set_notify(f"_read_client_status_{self.team}_{self.slot}")
            # Enable death link
            Utils.async_start(self.update_death_link(True))
            # Goal status event that triggers when
            self._goal_status_ready = asyncio.Event()
            # Get slot data
            if not self._get_slot_data(args):
                return
            self.slot_data_empty_once = False
            # Start launcher and communication handler.
            self._startup_task = asyncio.create_task(self._delayed_startup())

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

    async def disconnect(self, allow_autoreconnect: bool = False) -> None:
        await super().disconnect(allow_autoreconnect)

    async def connection_closed(self) -> None:
        self.game_id = None
        self.is_game_connected = False
        self.host_world_version = None
        self.slot_name = None
        # Disconnecting shouldn't stop the loop, only closing the app, or connecting to a different slot

        # self.interface_stop = self.communication_interface.stop()
        # await self.interface_stop

        # last_package = self.communication_interface.consume_outgoing()
        # if last_package is not None:
        #    await self._process_game_package(last_package)

        await super().connection_closed()

    def _is_socket_open(self) -> bool:
        return self.server is not None and not self.server.socket.closed

    def _is_server_connected(self) -> bool:
        return self._is_socket_open() and self.slot is not None

    def get_khimera_damg_status(self) -> str:
        return (f"Server connected: {self._is_server_connected()},"
            f"\nGame connected: {self.is_game_connected},"
            f"\nSlot data: {self.slot_data}")

    def make_gui(self) -> type[kvui.GameManager]:
        ui = super().make_gui()
        ui.base_title = "Archipelago Khimera: Destroy All Monster Girls Client"
        return ui


def launch(*args: str) -> None:
    async def main() -> None:
        parser = get_base_parser(description="Khimera: Destroy All Monster Girls Client")
        parser.add_argument("--name", default=None, help="Slot name to connect as.")
        parser.add_argument("url", nargs="?", help="Archipelago connection url")

        parsed_args = handle_url_arg(parser.parse_args(args))

        ctx = KhimeraDAMGContext(parsed_args.connect, parsed_args.password)
        ctx.auth = parsed_args.name
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        await ctx.exit_event.wait()
        await ctx.shutdown()

    Utils.init_logging("KhimeraDAMGClient", exception_logger="Client")

    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
