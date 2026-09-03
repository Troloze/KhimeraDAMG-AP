from __future__ import annotations

from pathlib import Path
from subprocess import Popen

from . import GAME_ID

# from .client import get_storage_path

# import asyncio


class PatchInfo:
    _local_path: str

    def __init__(self, name: str) -> None:
        self.local_path = name

    @property
    def local_path(self) -> str:
        return self._local_path

    @local_path.setter
    def local_path(self, value: str) -> None:
        self._local_path = f"ap:{GAME_ID}/patches/{value}"


# Currently selecting individually, a better approach would be to create
# version ranges (i.e. from 0.0.2 to 0.1.3 use patch 0, from 0.1.4 to 0.1.7 use patch 1, ...)
# but for the purposes of an unfinished skeleton this works fine to illustrate the point.
version_to_patch: dict[str, PatchInfo] = {
    "0.0.2": PatchInfo("p0.diff")  # Doesn't exist yet
}


# Unimplemented Skeleton, deliberately does not work.
class KhimeraDAMGLauncher:
    def __init__(self) -> None:
        self.stored_data_validated = self._validate_stored_data()
        self.game_process: Popen[bytes] | None = None

    def launch_game(self, host_version: str) -> None:
        if self.is_game_running:
            return
        if not self._handle_patch(host_version):
            raise RuntimeError
        # self.game_process = Popen("game_process", cwd=str(self._get_storage_folder))

    @property
    def is_game_running(self) -> bool:
        if self.game_process is None:
            return False
        if self.game_process.poll() is None:
            return True
        self.game_process = None
        return False

    def _validate_stored_data(self) -> bool:
        if not self._has_stored_files():
            install_path = self._search_in_steam_library()
            if install_path is None:
                install_path = self._prompt_for_game_location()
                if install_path is None:
                    # Fail logic, to be defined later.
                    # For now can do nothing since there isn't a mod anyways
                    return True
            return self._store_files(install_path)
        return True

    def _has_stored_files(self) -> bool:
        return True

    def _search_in_steam_library(self) -> Path | None:
        pass

    def _prompt_for_game_location(self) -> Path | None:
        pass

    def _store_files(self, _path: Path) -> bool:
        return True

    def _handle_patch(self, host_version: str) -> bool:
        # Hash current patched files to see if patch is the correct one for this version
        # If not, delete current data.win, and make a new data.win with the correct patch.
        # Returns false on patch failure.
        _patch: PatchInfo = version_to_patch[host_version]
        return True
