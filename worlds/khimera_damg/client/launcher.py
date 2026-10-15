from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
import Utils  # type: ignore

from .. import APWORLD_VERSION
from .patcher import FailedToBuildError, SourceNotFoundError, executable_name, load_patch, try_load_build
from .storage import KhimeraDAMGStorageHandler

if TYPE_CHECKING:
    import kvui  # type: ignore

    from .client import KhimeraDAMGContext  # Will cause a circular import normally

logger = logging.getLogger("Client")


class LauncherError(Exception):
    pass


class GameNotFoundError(LauncherError):
    pass


# Unimplemented Skeleton, deliberately does not work.
class KhimeraDAMGLauncher:
    def __init__(self, ctx: KhimeraDAMGContext) -> None:
        self.pid: int | None = None
        self.ctx: KhimeraDAMGContext = ctx
        self.process: psutil.Process | None = None
        self.process_creation_time: float | None = None
        self.address: str | None = None
        self.apw_version: str | None = None
        self.slot_name: str | None = None
        self.game_id: str | None = None
        self._tracking: bool = False
        self.try_connect_to_last_session()

    @property
    def tracking(self) -> bool:
        self.update_launcher_state()
        return self._tracking

    async def launch_game(
        self,
        host_version: str,
        host_address: str,
        slot_name: str,
        game_id: str,
    ) -> int | None:
        if self.tracking:
            return None
        try:
            await asyncio.to_thread(load_patch, host_version)
        except SourceNotFoundError as err:
            path = await self._launch_prompt()
            if path is None:
                raise GameNotFoundError(
                    f"There is no game to be launched for the host version: {host_version}."
                ) from err
            load_success = False
            try:
                load_success = await asyncio.to_thread(try_load_build, path)
            except (OSError, SourceNotFoundError) as err2:
                msg = self._message("Couldn't load build", "Please try again later.", error=True)
                logger.warning("Couldn't load build, please try again later.")
                if msg is not None:
                    msg.open()
                raise err2
            if load_success:
                try:
                    await asyncio.to_thread(load_patch, host_version)
                except Exception as err2:
                    msg = self._message(
                        "Couldn't load build",
                        "The import was successful, but it was not possible to load the build.",
                        error=True
                    )
                    logger.warning(
                        "The import was successful, but it was not possible to load the build."
                    )
                    if msg is not None:
                        msg.open()
                    raise FailedToBuildError(
                        "The import was successful, but it was not possible to load the build."
                    ) from err2

        self.ctx.reset_connection_state()
        logger.info("Launching game...")
        game_folder = KhimeraDAMGStorageHandler.get_path_raw(folder="loaded_patch")
        uid = int(time.time())  # Safe for around 285.4 million years! (since August 15 2026, 00h18 UTC-3).
        process = psutil.Popen([str(game_folder / executable_name), f"--launcher_uid={uid}"], cwd=game_folder)

        c_time = process.create_time()
        url = urllib.parse.urlparse(host_address)

        self.pid = process.pid
        self.process = process
        self.process_creation_time = c_time
        self._tracking = True
        self.address = f"{url.scheme}://{url.netloc.rpartition('@')[2]}"
        self.apw_version = APWORLD_VERSION
        self.slot_name = slot_name
        self.game_id = game_id

        last_session = {
            "pid": self.pid,
            "apw_version": self.apw_version,
            "create_time": self.process_creation_time,
            "address": self.address,
            "name": self.slot_name,
            "game_id": self.game_id
        }
        KhimeraDAMGStorageHandler.store(key="last_session", value=last_session, file_name="meta", category="launcher")

    def _terminate(self) -> bool:
        if self.process is None:
            return False

        if os.name == "nt":  # windows
            # Lack of /f makes it a graceful call.
            proc = subprocess.run(
                ["taskkill", "/PID", str(self.process.pid)],
                capture_output=True,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if proc.returncode != 0:
                logger.warning(f"Failed to send the termination signal: {proc.stderr.strip()}")
                return False
        else:
            self.process.terminate()  # Closes process gracefully in linux and mac.

        logger.info(
            "Termination signal has been successfully sent to the game process. "
            "Note that the game may not close immediately, and in case of freezing you may need to "
            "wait it out (or kill the process manually)."
        )
        return True

    async def terminate(self) -> None:
        if not self.tracking:
            logger.warning("Failed attempt to close the game: There are no game processes being tracked.")
            return
        try:
            await asyncio.to_thread(self._terminate)
        except psutil.NoSuchProcess:
            self.reset_tracking()
            logger.warning("Failed attempt to close the game: Process not found.")
        except psutil.AccessDenied:
            logger.warning("Failed attempt to close the game: Permission denied.")

    def try_connect_to_last_session(self) -> bool:
        last_session: dict = KhimeraDAMGStorageHandler.get(
            key="last_session",
            file_name="meta",
            category="launcher"
        )
        if last_session is None:
            return False
        pid = last_session.get("pid")
        apw_version = last_session.get("apw_version")
        create_time = last_session.get("create_time")
        address = last_session.get("address")
        name = last_session.get("name")
        game_id = last_session.get("game_id")
        if (
            pid is None or
            not isinstance(pid, int) or
            apw_version is None or
            not isinstance(apw_version, str) or
            create_time is None or
            not isinstance(create_time, float) or
            address is None or
            not isinstance(address, str) or
            name is None or
            not isinstance(name, str) or
            game_id is None or
            not isinstance(game_id, str)
        ):
            # Remove malformed last_session info.
            KhimeraDAMGStorageHandler.store(
                key="last_session",
                value=None,
                file_name="meta",
                category="launcher"
            )
            self.reset_tracking()
            return False
        connected, process = self.probe_game_status(pid, create_time)
        if not connected or process is None:
            # last_session is well formatted, so we don't remove it.
            self.reset_tracking()
            return False
        self.pid = pid
        self.process = process
        self.apw_version = apw_version
        self.process_creation_time = create_time
        self.address = address
        self.slot_name = name
        self.game_id = game_id
        self._tracking = True
        return True

    def reset_tracking(self) -> None:
        self.pid = None
        self.process = None
        self.apw_version = None
        self.process_creation_time = None
        self.address = None
        self.slot_name = None
        self.game_id = None
        self._tracking = False

    @staticmethod
    def probe_game_status(
        pid: int | None = None,
        creation_time: float | None = None,
        *,
        launcher: KhimeraDAMGLauncher | None = None
    ) -> tuple[bool, psutil.Process | None]:
        if launcher is not None:
            if (
                not launcher._tracking or  # NOT ".tracking", otherwise we get an infinite recursion.
                launcher.process is None or
                launcher.process_creation_time is None or
                not launcher.process.is_running()
            ):
                return False, None
            return True, launcher.process
        if pid is None or creation_time is None:
            return False, None
        try:
            entry = psutil.Process(pid)
            name = Path(entry.exe()).name
            c_time = entry.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False, None
        return name == executable_name and c_time == creation_time, entry

    def update_launcher_state(self) -> bool:
        connected, _ = self.probe_game_status(launcher=self)
        if not connected:
            self.reset_tracking()
            return False
        return True

    def _search_in_steam_library(self) -> Path | None:
        raise NotImplementedError("Steam Library search is not available yet")

    # Generic prompt builder
    async def _prompt(
        self,
        title: str,
        description: str,
        buttons: tuple[str, ...],
        *,
        auto_dismiss: bool = False
    ) -> str | None:
        if not Utils.is_kivy_running():
            return None
        # Has to be imported late to ensure it only is imported when GUI is enabled.
        import kvui  # type: ignore

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()

        def on_action(action: str) -> None:
            if not future.done():
                future.set_result(action)

        prompt = kvui.ButtonsPrompt(title, description, on_action, *buttons, auto_dismiss=False)
        prompt.open()

        try:
            return await future
        finally:
            prompt.dismiss()

    def _message(
        self,
        title: str,
        description: str,
        *,
        auto_dismiss: bool = False,
        error: bool = False
    ) -> kvui.MessageBox | None:
        if not Utils.is_kivy_running():
            return None
        # Has to be imported late to ensure it only is imported when GUI is enabled.
        import kvui  # type:ignore

        return kvui.MessageBox(title, description, error, auto_dismiss=auto_dismiss)

    async def _prompt_build_directory(self) -> Path | None:
        loading_message = self._message(
            "Waiting for a build",
            "Please select the folder of a \"Khimera: Destroy All Monster Girls\" build",
            auto_dismiss=True
        )

        folder_prompt = asyncio.to_thread(
            Utils.open_directory,
            "Open vanilla build"
        )
        if loading_message is not None:
            loading_message.open(animation=False)

        folder = await folder_prompt

        if loading_message is not None:  # Dismissed by being done with the folder selector, if not dismissed already
            loading_message.dismiss(force=True, animation=False)

        if folder is None or folder == "":
            return None

        return Path(folder)

    async def startup_prompt(self) -> Path | None:
        skip_prompt = KhimeraDAMGStorageHandler.get(key="skip_startup_prompt", file_name="meta", category="launcher")
        if skip_prompt == APWORLD_VERSION:
            return None
        if not Utils.is_kivy_running():
            return None

        buttons: tuple[str, ...] = (
            "Open vanilla build",
            "Dismiss",
            "Don't ask again"
        )
        action = await self._prompt(
            "No source detected",
            (
                "No vanilla build of \"Khimera: Destroy All Monster Girls\" "
                "compatible with this version of the APWorld was found.\n"
                "This APWorld requires a vanilla build in order to be used; you may still be able to "
                "connect to a game without it, but you will not be able to play the game."
            ),
            buttons
        )
        if action is None or action == "Dismiss":
            return None
        if action == "Don't ask again":
            KhimeraDAMGStorageHandler.store(
                key="skip_startup_prompt",
                value=APWORLD_VERSION,
                file_name="meta",
                category="launcher"
            )
            return None
        # action = Open vanilla build

        return await self._prompt_build_directory()

    async def _launch_prompt(self) -> Path | None:
        buttons: tuple[str, ...] = (
            "Open vanilla build",
            "Cancel",
        )
        action = await self._prompt(
            "No source detected",
            (
                "There is no vanilla build of \"Khimera: Destroy All Monster Girls\" loaded currently.\n"
                "Please provide a build of the game."
            ),
            buttons
        )
        if action is None or action == "Cancel":
            return None
        return await self._prompt_build_directory()
