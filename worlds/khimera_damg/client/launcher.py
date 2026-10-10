from __future__ import annotations

from pathlib import Path
from subprocess import Popen


# Unimplemented Skeleton, deliberately does not work.
class KhimeraDAMGLauncher:
    def __init__(self) -> None:
        self.game_process: Popen[bytes] | None = None

    def launch_game(self, host_version: str) -> None:
        if self.is_game_running:
            return

        # self.game_process = Popen("game_process", cwd=str(self._get_storage_folder))

    @property
    def is_game_running(self) -> bool:
        if self.game_process is None:
            return False
        if self.game_process.poll() is None:
            return True
        self.game_process = None
        return False

    def _has_stored_files(self) -> bool:
        return True

    def _search_in_steam_library(self) -> Path | None:
        pass

    def _prompt_for_game_location(self) -> Path | None:
        pass
