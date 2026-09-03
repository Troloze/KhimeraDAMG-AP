from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import Utils
from CommonClient import (
    ClientCommandProcessor,
    ClientStatus,
    CommonContext,
    get_base_parser,
    gui_enabled,
    handle_url_arg,
    logger,
    server_loop,
)
from NetUtils import JSONMessagePart, JSONtoTextParser

from . import GAME_ID
from .game_communication import KhimeraCommunicationHandler
from .launcher import KhimeraDAMGLauncher

if TYPE_CHECKING:
    import kvui

def get_storage_path() -> Path:
    return Path(Utils.user_path(GAME_ID))

class KhimeraDAMGJSONToTextParser(JSONtoTextParser):
    def _handle_color(self, node: JSONMessagePart) -> str:
        return self._handle_text(node)  # No colors for the in-game text

class KhimeraDAMGCommandProcessor(ClientCommandProcessor):
    def _cmd_force_win(self) -> None:
        if isinstance(self.ctx, KhimeraDAMGContext):
            if self.ctx.communication_handler is not None:
                self.ctx.communication_handler.on_goal()


    def _cmd_khimera_damg(self) -> None:
        """Check Khimera DAMG Connection State"""
        if isinstance(self.ctx, KhimeraDAMGContext):
            logger.info(f"KhimeraDAMG Status:  {'{'}\n{self.ctx.get_khimera_damg_status()}\n{'}'}")

class KhimeraDAMGContext(CommonContext):
    command_processor = KhimeraDAMGCommandProcessor
    game = "Khimera: Destroy All Monster Girls"
    items_handling = 0b111

    def __init__(self, server_address: str | None = None, password: str | None = None) -> None:
        super().__init__(server_address, password)
        self.launcher: KhimeraDAMGLauncher = KhimeraDAMGLauncher()
        self.slot_data: dict[str, Any] = {}
        self.communication_handler: KhimeraCommunicationHandler | None = None

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)

        await self.get_username()
        await self.send_connect()

    def start_up_game_processes(self) -> None:
        host_apworld_version: str = self.slot_data["apworld_version"]
        if self.communication_handler is None:
            self.communication_handler = KhimeraCommunicationHandler(self)
        if not self.launcher.is_game_running:
            if self.launcher.stored_data_validated:
                self.launcher.launch_game(host_apworld_version)

    async def disconnect(self, allow_autoreconnect: bool = False) -> None:
        await super().disconnect(allow_autoreconnect)
        if self.communication_handler is not None:
            self.communication_handler.update_host_connection_status(False)

    def _get_slot_data(self, args) -> bool:
        self.slot_data = args.get("slot_data", {})
        if len(self.slot_data) == 0:
            logger.warning('"slot_data" is empty, closing the connection.')
            if not self.__slot_data_empty_once:
                self.__slot_data_empty_once: bool = True
                Utils.async_start(self.disconnect(True))
            else:
                Utils.async_start(self.disconnect(False))
            return False
        return True

    def on_package(self, cmd: str, args: dict) -> None:
        super().on_package(cmd, args)
        if cmd == "Connected":
            # Enable death link
            Utils.async_start(self.update_death_link(True))
            # Get slot data
            if not self._get_slot_data(args):
                return
            # Start launcher and communication handler.
            try:
                self.start_up_game_processes()
            except Exception:
                logger.exception("Khimera setup failed; server connection remains active.")
            # Resend win condition on connection in case it was sent while disconnected.
            if self.finished_game:
                Utils.async_start(self.send_msgs(
                [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]))

    def on_deathlink(self, data: dict[str, Any]) -> None:
        if self.communication_handler is not None:
            self.communication_handler.send_deathlink()
        return super().on_deathlink(data)

    async def connection_closed(self) -> None:
        if self.communication_handler is not None:
            self.communication_handler.update_host_connection_status(False)
        await super().connection_closed()

    def is_socket_open(self) -> bool:
        return self.server is not None and not self.server.socket.closed

    def is_server_connected(self) -> bool:
        return self.is_socket_open() and self.slot is not None

    def get_khimera_damg_status(self) -> str:
        is_game_connected = False
        if self.communication_handler is not None:
            is_game_connected = self.communication_handler.is_connected()
        return f"Server connected: {self.is_server_connected()},\
            \nGame connected: {is_game_connected},\
            \nSlot data: {self.slot_data}"

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
