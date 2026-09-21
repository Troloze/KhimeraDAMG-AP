from __future__ import annotations

import asyncio
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import Utils  # type: ignore
import yaml
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

from . import APWORLD_VERSION, GAME_ID
from .communication import KhimeraDAMGCommunicationInterface
from .launcher import KhimeraDAMGLauncher
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

    def __init__(self, ctx: CommonContext) -> None:
        super().__init__(ctx)
        self.continue_context: str | None = None
        self.continue_time: float | None = None

    def _cmd_force_win(self) -> None:
        """ DEBUG COMMAND.\nForces a win """
        self.continue_context = None
        self.continue_time = None
        if isinstance(self.ctx, KhimeraDAMGContext):
            Utils.async_start(self.ctx.send_msgs(
                [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
            ))

    def _cmd_status(self) -> None:
        """Check Khimera DAMG Connection State"""
        self.continue_context = None
        self.continue_time = None
        if isinstance(self.ctx, KhimeraDAMGContext):
            logger.info(self.ctx.get_khimera_damg_status())

    def _cmd_export_game_data(self) -> None:
        """
            [ DOES NOT WORK AT THE MOMENT ]
            Requires connection.
            Exports a copy of the stored game data for the currently loaded slot.
            Import it using import game data.
        """
        # Check if the slot is connected.
        self.continue_context = None
        self.continue_time = None

    def _cmd_reset_game_data(self) -> None:
        """
            [ DOES NOT WORK AT THE MOMENT ]
            Requires connection.
            Deletes the stored game data for the currently loaded slot.
            Running this command will destroy your safe file.

            This operation is irreversible and can cause data loss, make sure you know what you're doing.
        """
        # Check if the slot is connected.
        self.continue_context = "reset"
        self.continue_time = time.perf_counter()
        logger.info("This operation is irreversible and can cause data loss.")
        logger.info("Send /confirm in order to reset your game data.")

    def _cmd_wipe_all_game_data(self) -> None:
        """
            [ DOES NOT WORK AT THE MOMENT ]
            Deletes all the stored game data.
            Running this command will destroy every save file you have in your computer.

            This operation is irreversible, make sure you know what you're doing.
        """
        self.continue_context = "wipe"
        self.continue_time = time.perf_counter()
        logger.info("This operation is irreversible.")
        logger.info("Send /confirm in order to wipe the game data.")

    def _cmd_wipe_all_but_current(self) -> None:
        """
            [ DOES NOT WORK AT THE MOMENT ]
            Requires connection.
            Deletes all the stored game data, except for the current slot.
            Running this command will destroy every other save file you have in your computer.

            This operation is irreversible, make sure you know what you're doing.
        """
        # Check if the slot is connected.
        self.continue_context = "wipe"
        self.continue_time = time.perf_counter()
        logger.info("This operation is irreversible.")
        logger.info("Send /confirm in order to wipe the game data.")

    def _cmd_import_game_data(self) -> None:
        """
            [ DOES NOT WORK AT THE MOMENT ]
            Requires connection.
            Loads and exported copy of the game data for the currently loaded slot.
            Note that this requires the exported data's slot to match the currently loaded one.

            This operation is irreversible and can cause data loss, make sure you know what you're doing.
        """
        # Check if the slot is connected.
        self.continue_context = "import"
        self.continue_time = time.perf_counter()
        logger.info("This operation is irreversible and can cause data loss.")
        logger.info("Send /confirm in order to import your game data.")

    def _cmd_confirm(self) -> None:
        """
            Confirmation command, does nothing on its own.
            Once a dangerous command is issued, you will be asked to use this.
        """
        if self.continue_context is None or self.continue_time is None:
            logger.info("Nothing to confirm.")
            return
        if self.continue_time < time.perf_counter() - self.continue_timeout:
            logger.info("You took too long to confirm, please try again.")
            self.continue_time = None
            self.continue_context = None
            return
        if self.continue_context == "wipe":
            self.continue_context = "wipe_"
            self.continue_time = time.perf_counter()
            logger.info("This will delete every single saved file in your machine."
                        " Are you absolutely sure this is what you want to do?")
            logger.info("Send /confirm again in order to wipe the game data. (LAST WARNING)")
            return
        if self.continue_context == "wipe_":
            # Wipe everything.
            self.continue_context = None
            self.continue_time = None
            return
        if self.continue_context == "wipe_but":
            self.continue_context = "wipe_but_"
            self.continue_time = time.perf_counter()
            logger.info("This will delete every single saved file in your machine other than the currently loaded one."
                " Are you absolutely sure this is what you want to do?")
            logger.info("Send /confirm again in order to wipe all game data other than the currently loaded."
                "(LAST WARNING)")
            return
        if self.continue_context == "wipe_but_":
            # Wipe everything, but the current slot.
            self.continue_context = None
            self.continue_time = None
            return
        if self.continue_context == "reset":
            # Deletes the current slot's storage yaml
            self.continue_time = None
            self.continue_context = None
            return
        if self.continue_context == "import":
            _imp_path = Path()  # Import path
            # check if is yaml
            # get slot information (name and seed).
            # verify if they match with the current context
            # find a way to swap the
            self.continue_time = None
            self.continue_context = None
            return


class KhimeraDAMGStorageHandler:
    @staticmethod
    def _get_path(game_id: str) -> Path:
        path = Path(Utils.user_path(GAME_ID))
        if not path.exists():
            path.mkdir(parents=True)
        # No benefit from hashing this other than obfuscation, bad for testing.
        file_name = f"{game_id}.yaml"
        return path / file_name

    @classmethod
    def _get_data(cls, game_id: str) -> Any:
        path = cls._get_path(game_id)
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text())
        # We do not want lists here, so, just to be safe, let's drop the data if it is a list.
        if not isinstance(data, dict):
            data = {}
        return data

    @classmethod
    def _set_data(cls, data: Any, game_id: str) -> None:
        base = cls._get_path(game_id)
        tmp = base.parent / (base.name + ".tmp")
        tmp.write_text(yaml.dump(data))
        os.replace(tmp, base)

    @classmethod
    def store(cls, key: str, value: Any, game_id: str, category: str | None = None) -> None:
        """Value has to be yaml-able."""
        data: dict = cls._get_data(game_id)
        if category is None:
            if value is None:
                data.pop(key, "")
            else:
                data[key] = value
        else:
            cat_data = data.get(category)
            if cat_data is None:
                cat_data = {}
            if value is None:
                cat_data.pop(key, "")
            else:
                cat_data[key] = value
            data[category] = cat_data
        cls._set_data(data, game_id)

    @classmethod
    def store_many(cls, keys: list[str], values: list[Any], game_id: str, category: str | None = None) -> None:
        data: dict = cls._get_data(game_id)
        if not len(keys) == len(values):
            raise ValueError("Keys and values must have the same number of elements")
        for i in range(len(keys)):
            if category is None:
                if values[i] is None:
                    data.pop(keys[i], "")
                else:
                    data[keys[i]] = values[i]
            else:
                cat_data = data.get(category)
                if cat_data is None:
                    cat_data = {}
                if values[i] is None:
                    cat_data.pop(keys[i], "")
                else:
                    cat_data[keys[i]] = values[i]
                data[category] = cat_data
        cls._set_data(data, game_id)

    # Allows getting a whole category by passing its name as a key.
    @classmethod
    def get(cls, key: str, game_id: str, default: Any = None, category: str | None = None) -> Any:
        data: dict = cls._get_data(game_id)
        if category is None:
            return data[key] if key in data else default
        if category in data:
            cat_data = data[category]
            return cat_data[key] if key in cat_data else default
        return default


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

    async def _start_up_game_processes(self) -> None:
        last_ack = KhimeraDAMGStorageHandler.get("last_ack", self.game_id, 0)  # type: ignore
        items = self.items_received  # Accessed asynchronously, state can change between a loop's readings
        item_list = [(i + 1, items[i]) for i in range(0, len(items))]
        win_status = self.stored_data.get(f"_read_client_status_{self.team}_{self.slot}")
        # Resolves to "False" if win_status is None
        is_win = win_status == ClientStatus.CLIENT_GOAL
        # This will return the entirety of the "game_data" category.
        game_data = KhimeraDAMGStorageHandler.get("game_data", self.game_id, {})  # type: ignore
        self.cctx = ConnectionContext(
            ap_version=Utils.__version__,
            host_world_version=self.host_world_version,  # type: ignore
            client_world_version=APWORLD_VERSION,
            slot_name=self.slot_name,  # type: ignore
            seed=self.host_seed,  # type: ignore
            last_ack=last_ack,
            options=self.slot_data["options"],
            slot_data=self.slot_data["data"],
            game_data=game_data,
            locations=self.checked_locations,
            item_list=item_list,
            has_goaled=is_win
        )
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
        if (
            self.communication_interface is None or
            not self.communication_interface.authenticate(self.slot_name, self.host_seed)  # type: ignore
        ):
            try:
                await self._start_up_game_processes()
            except Exception:
                logger.exception("Khimera setup failed; server connection remains active.")

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
