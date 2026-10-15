from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path
from typing import Any

import Utils  # type: ignore
import yaml

from .. import GAME_ID


class KhimeraDAMGStorageHandler:
    @staticmethod
    def _get_path(file_name: str | None, folder: str | None) -> Path:
        base_path = Path(Utils.user_path(GAME_ID)).resolve()
        folder_path = base_path
        if folder is not None and folder != "":
            folder_path = (folder_path / folder).resolve()
            if not folder_path.is_relative_to(base_path):
                raise ValueError(
                    f"Invalid folder name would've caused a write outside of the designated folder. \"{folder}\""
                )
        if not folder_path.exists():
            folder_path.mkdir(parents=True)
        file_name_formatted = f"{file_name}.yaml"
        return_path = (folder_path / file_name_formatted).resolve()
        if not return_path.is_relative_to(base_path):
            raise ValueError(
                f"Invalid file name would've caused a write outside of the designated folder: \"{file_name}\""
            )
        return return_path

    @staticmethod
    def get_path_raw(file_name: str | None = None, folder: str | None = None, *, skip_mkdir: bool = False) -> Path:
        base_path = Path(Utils.user_path(GAME_ID)).resolve()
        folder_path = base_path
        if folder is not None and folder != "":
            folder_path = (folder_path / folder).resolve()
            if not folder_path.is_relative_to(base_path):
                raise ValueError(
                    f"Invalid folder name would've caused a write outside of the designated folder. \"{folder}\""
                )
        if not folder_path.exists() and not skip_mkdir:
            folder_path.mkdir(parents=True)
        return_path = (folder_path if file_name is None else folder_path / file_name).resolve()
        if not return_path.is_relative_to(base_path):
            raise ValueError(
                f"Invalid file name would've caused a write outside of the designated folder: \"{file_name}\""
            )
        return return_path

    @classmethod
    def _get_data(cls, file_name: str, folder: str | None) -> Any:
        path = cls._get_path(file_name, folder)
        if not path.exists():
            return {"id": file_name}
        try:
            data = yaml.safe_load(path.read_text())
        except (yaml.YAMLError, TypeError, KeyError):
            # Complete override, we don't have a better solution though.
            data = {}
        # We do not want lists here, so, just to be safe, let's drop the data if it is a list.
        if not isinstance(data, dict):
            data = {}
        data["id"] = file_name
        return data

    @classmethod
    def _set_data(cls, data: Any, file_name: str, folder: str | None) -> None:
        base = cls._get_path(file_name, folder)
        tmp = base.parent / (base.name + ".tmp")
        tmp.write_text(yaml.dump(data))
        os.replace(tmp, base)

    @classmethod
    def wipe(cls, exception: str | None) -> None:
        current = Path("")  # ""
        if exception is not None:
            current = cls._get_path(exception, "game_data")
        base_path = cls._get_path("", "game_data").parent

        for file in base_path.iterdir():
            if not file.is_file() or file.name == current.name or file.name[-4:] == ".tmp":
                continue
            file.unlink()

    @classmethod
    def probe_data(cls, file_name: str) -> bool:
        path = cls._get_path(file_name, "game_data")
        return path.exists()

    @classmethod
    async def save_data(cls, file_name: str) -> bool:
        if not cls.probe_data(file_name):
            return False
        file_path = await asyncio.to_thread(
            Utils.save_filename,
            "Export game data as...",
            [("Khimera DAMG data", [".kdamgdata"])],
            suggest=f"{file_name}.kdamgdata"
        )

        if file_path is None or file_path == "":
            return False

        destination_path = Path(file_path)
        source_path = cls._get_path(file_name, "game_data")

        if destination_path.exists():
            destination_path.unlink()
            if destination_path.exists():
                return False

        shutil.copy(source_path, destination_path)

        return destination_path.exists()

    @classmethod
    def probe_load(cls, file_name: str | None) -> str | None:
        if file_name is None or file_name == "":
            return None
        game_id: str | None = None
        with open(file_name, "r", encoding="utf-8-sig") as f:
            try:
                data: dict = yaml.safe_load(f.read())
                game_id = data["id"]
            except (yaml.YAMLError, TypeError, KeyError, UnicodeDecodeError):
                return None
        if game_id is None:
            return None
        if not isinstance(game_id, str) or re.fullmatch(r"^[0-9a-f]{32}$", game_id) is None:
            # Invalid game id
            return None
        data_path = cls._get_path(game_id, "game_data")
        return game_id if data_path.exists() else ""

    @classmethod
    def load_data(cls, file_name: str | None) -> bool:
        """Destructive! Handle with care."""
        if file_name is None or file_name == "":
            return False
        game_id: str | None = None
        with open(file_name, "r", encoding="utf-8-sig") as f:
            try:
                data: dict = yaml.safe_load(f.read())
                game_id = data["id"]
            except (yaml.YAMLError, TypeError, KeyError, UnicodeDecodeError):
                return False
        if game_id is None:
            return False
        if not isinstance(game_id, str) or re.fullmatch(r"^[0-9a-f]{32}$", game_id) is None:
            # Invalid game id
            return False
        data_path = cls._get_path(game_id, "game_data")
        if data_path.exists():
            data_path.unlink()
            if data_path.exists():
                return False

        shutil.copy(file_name, data_path)

        return data_path.exists()

    @classmethod
    def delete_data(cls, file_name: str) -> bool:
        data_path = cls._get_path(file_name, "game_data")
        if data_path.exists():
            data_path.unlink()
        return not data_path.exists()

    @classmethod
    def store(
        cls,
        key: str,
        value: Any,
        file_name: str,
        category: str | None = None,
        *,
        folder: str | None = None
    ) -> None:
        """Value has to be yaml-able."""
        data: dict = cls._get_data(file_name, folder)
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
        cls._set_data(data, file_name, folder)

    @classmethod
    def store_many(
        cls,
        keys: list[str],
        values: list[Any],
        file_name: str,
        category: str | None = None,
        *,
        folder: str | None = None
    ) -> None:
        data: dict = cls._get_data(file_name, folder)
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
        cls._set_data(data, file_name, folder)

    # Allows getting a whole category by passing its name as a key.
    @classmethod
    def get(
        cls,
        key: str,
        file_name: str,
        default: Any = None,
        category: str | None = None,
        *,
        folder: str | None = None
    ) -> Any:
        data: dict = cls._get_data(file_name, folder)
        if category is None:
            return data[key] if key in data else default
        if category in data:
            cat_data = data[category]
            return cat_data[key] if key in cat_data else default
        return default

    @classmethod
    def store_as_file(
        cls,
        data: bytes | str,
        file_name: str,
        *,
        folder: str | None = None
    ) -> Path:
        path = cls.get_path_raw(file_name, folder)
        tmp = path.parent / (path.name + ".tmp")
        if isinstance(data, bytes):
            with open(tmp, "wb") as f:
                f.write(data)
        elif isinstance(data, str):
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
        if tmp.exists():
            os.replace(tmp, path)
        return path
