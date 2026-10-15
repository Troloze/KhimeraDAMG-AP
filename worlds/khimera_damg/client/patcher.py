from __future__ import annotations

import hashlib
import io
import pkgutil
import re
import shutil
import time
import zipfile
from pathlib import Path

import bsdiff4

from ..patches import PatchData, builds, mod_versions, patch_map  # type: ignore
from .storage import KhimeraDAMGStorageHandler


class PatcherError(Exception):
    pass


# For errors that really shouldn't happen
class HowDidWeGetHereError(PatcherError):
    pass


class UnsupportedBuildError(PatcherError):
    pass


class APWorldVersionTooHighError(PatcherError):
    pass


class APWorldVersionTooLowError(PatcherError):
    pass


class SourceNotFoundError(PatcherError):
    pass


class FailedToBuildError(PatcherError):
    pass


class PatchNotFoundError(PatcherError):
    pass


class SourceCouldNotBeDeletedError(PatcherError):
    pass


# Takes the (host) apworld version as key, and returns the highest compatible mod version.
# Always remember to update when bumping world version.
apworld_to_mod_map: dict[tuple[int, int, int], tuple[int, int, int]] = {
    (0, 0, 9): (0, 1, 0)
}

_patch_map_str: dict[tuple[str, str], PatchData] = {
    (".".join([str(entry) for entry in key[0]]), key[1]): value for key, value in patch_map.items()
}

_supported_build_hashes: dict[str, str] = {entry.name: entry.hash_id for entry in builds.values()}

_supported_build_hashes_inverted: dict[str, str] = {entry.hash_id: entry.name for entry in builds.values()}

_patch_builds: dict[tuple[int, int, int], list[str]] = {entry.name_id: entry.builds for entry in mod_versions.values()}

# Complex comprehension to avoid needing to copy+paste the same hashes over and over.
# This maps a mod version to a dictionary that in turn maps a hash into the build name.
source_map: dict[tuple[int, int, int], dict[str, str]] = {
    key: {
        h_value: h_key for h_key, h_value in _supported_build_hashes.items() if h_key in value
    }
    for key, value in _patch_builds.items()
}

max_build_size = max((build.total_size for build in builds.values()), default=0)
max_source_data_size = max((build.size for build in builds.values()), default=0)
max_apworld = max(apworld_to_mod_map.keys(), default=(0, 0, 0))
min_apworld = (0, 0, 9)  # Update to (0, 1, 0) on the first release, and keep it.

executable_name = "khimera_damg_ap_randomizer.exe"


def _make_hash_name(build_name: str, mod_version: tuple[int, int, int] | str) -> str:
    if isinstance(mod_version, tuple):
        mod_version = ".".join([str(i) for i in mod_version])
    return f"{mod_version}_{build_name}.txt"


def _make_patch_name(build_name: str, mod_version: tuple[int, int, int] | str) -> str:
    if isinstance(mod_version, tuple):
        mod_version = ".".join([str(i) for i in mod_version])
    return f"{mod_version}_{build_name}.win"


def _decompose_patch_name(patch_name: str) -> tuple[str, str]:
    match = re.match(r"[\w.-]*_[\w.-]*\.win$", patch_name)
    if match is None:
        raise ValueError("Invalid patch name structure")
    decomposed = patch_name[:-4].split("_", 1)
    return (decomposed[0], decomposed[1])


def _get_mod_version(apw_version: str) -> tuple[int, int, int]:
    try:
        digits = tuple(map(int, apw_version.split(".")))
    except (TypeError, ValueError) as err:
        raise ValueError("Version strings must be composed of 3 numbers separated by dots.") from err
    if len(digits) != 3:
        raise ValueError("Version strings must be composed of 3 numbers separated by dots.")
    if digits > max_apworld:
        raise APWorldVersionTooHighError(
            "The version of the host apworld is too high for this client. "
            "Please update the KhimeraDAMG apworld"
        )
    if digits < min_apworld:
        raise APWorldVersionTooLowError(
            "The version of the host apworld is too low for this client. "
            "This error shouldn't ever happen; if you haven't messed with the "
            "apworld, please report this to the dev"
        )  # Genuinely impossible to happen under normal circumstances.
    # This function is barely ever called and the lookup dictionary will never be big enough.
    # It's ok for this to stay suboptimal.
    mod_digits: tuple[int, int, int] | None = max((k for k in apworld_to_mod_map if k <= digits), default=None)
    if mod_digits is None:
        raise ValueError(f'Version "{apw_version}" is not valid')

    return apworld_to_mod_map[mod_digits]


def _get_source_map(mod_version: tuple[int, int, int]) -> dict[str, str]:
    # This function is barely ever called and the lookup dictionary will never be big enough.
    # It's ok for this to stay suboptimal.
    key: tuple[int, int, int] | None = max((k for k in source_map if k <= mod_version), default=None)
    if key is None:
        raise ValueError(f'Version "{mod_version}" is not valid')
    return source_map[key]


# Checks if the current loaded data.win is supported
# Returns the data.win build name
def _check_source_build(source_path: Path, mod_version: tuple[int, int, int]) -> str:
    p_map = _get_source_map(mod_version)
    source_data = Path(source_path) / "data.win"

    with open(source_data, "rb") as f:
        g_hash_ = hashlib.file_digest(f, "md5")
    g_hash = g_hash_.hexdigest()
    if g_hash not in p_map:
        raise UnsupportedBuildError("This build is not supported")
    return p_map[g_hash]


# check_source_build should be called before this, so it is safe to assume
# the build will exist within the patch version.
def _find_diff(build_name: str, mod_version: tuple[int, int, int]) -> bytes:
    # __package__ returns khimera_damg/client, so we pop its tail off.
    world = __package__.rsplit(".", 1)[0]  # type:ignore
    version_str = ".".join([str(i) for i in mod_version])
    version_zip = pkgutil.get_data(world, f"patches/{version_str}.zip")
    if version_zip is None:
        raise FileNotFoundError(f"Could not find {version_str}.zip")
    buffer = io.BytesIO(version_zip)

    with zipfile.ZipFile(buffer, "r") as zip_ref:
        # Raises KeyError if not found, the caller should catch it like the others.
        # But it genuinely should not happen unless the version_zip is messed with.
        return zip_ref.read(f"{build_name}/kdamg_diff.bsdiff4")


def _patch(build_name: str, apw_version: str) -> Path:
    mod_version = _get_mod_version(apw_version)
    source_path = KhimeraDAMGStorageHandler.get_path_raw(folder=f"source/{build_name}")
    source_data = source_path / "data.win"
    diff = _find_diff(build_name, mod_version)
    with open(source_data, "rb") as f:
        source = f.read()

    output: bytes = bsdiff4.patch(source, diff)
    output_hash = hashlib.md5(output).hexdigest()
    patch = patch_map.get((mod_version, build_name))
    if patch is None:
        raise HowDidWeGetHereError(
            "This exception should've been raised earlier, if this was raised something is very wrong."
        )
    if not output_hash == patch.hash_id:
        raise RuntimeError('Patched "data.win" does not match the hash signature.')

    output_path = KhimeraDAMGStorageHandler.store_as_file(
        output,
        _make_patch_name(build_name, mod_version),
        folder="patches"
    )
    KhimeraDAMGStorageHandler.store_as_file(output_hash, _make_hash_name(build_name, mod_version), folder="patches")

    return output_path


def _find_patch(build_name: str, apw_version: str) -> Path:
    mod_version = _get_mod_version(apw_version)

    hash_file = KhimeraDAMGStorageHandler.get_path_raw(_make_hash_name(build_name, mod_version), "patches")
    patch_file = KhimeraDAMGStorageHandler.get_path_raw(_make_patch_name(build_name, mod_version), "patches")
    if not hash_file.exists() or not patch_file.exists():
        hash_file.unlink(missing_ok=True)
        patch_file.unlink(missing_ok=True)
        raise PatchNotFoundError

    patch_hash = hash_file.read_text(encoding="utf-8-sig")

    patch = patch_map.get((mod_version, build_name))
    if patch is None:
        raise HowDidWeGetHereError("If this is raised, something is very wrong.")
    if not patch_hash == patch.hash_id:
        patch_file.unlink()
        raise PatchNotFoundError
    return patch_file


def rebuild_patch(patch_path: Path, apw_version: str) -> None:
    try:
        version, build = _decompose_patch_name(patch_path.name)
    except Exception as err:
        raise ValueError("Provided file name is not valid.") from err

    hash_path = KhimeraDAMGStorageHandler.get_path_raw(_make_hash_name(build, version), "patches")

    hash_path.unlink(missing_ok=True)
    patch_path.unlink(missing_ok=True)

    source_list = source_get(apw_version, build_name=build)

    if len(source_list) == 0:
        raise SourceNotFoundError("Could not find the source path.")

    _patch(source_list[0], apw_version)


def patch_validate(patch_path: Path) -> bool:
    if not patch_path.exists():
        return False
    try:
        version, build = _decompose_patch_name(patch_path.name)
    except ValueError:
        return False
    patch = _patch_map_str.get((version, build))
    if patch is None:
        return False
    if patch_path.stat().st_size != patch.size:
        return False

    # We do not handle OSError since it is not an issue with the data.
    # The caller should handle it.
    patch_data = patch_path.read_bytes()

    test_hash = hashlib.md5(patch_data).hexdigest()
    if patch.hash_id != test_hash:
        return False

    return True


# Raises UnsupportedBuildError when source_path build is not compatible with apw_version.
# Raises ValueError when the version is not valid.
# All other Exceptions raised should not happen under normal circumstances, so let them explode.
def get_patch(source_path: Path, apw_version: str) -> Path:
    mod_version = _get_mod_version(apw_version)
    build = _check_source_build(source_path, mod_version)
    try:
        patch_path = _find_patch(build, apw_version)
    except PatchNotFoundError:  # There are other exceptions, but they won't be handled here
        patch_path = _patch(build, apw_version)

    return patch_path


def _hash_multiple_files(file_list: list[Path]) -> str:
    source_hash = hashlib.new("md5")

    # WARNING: Needs to match KhimeraDAMG-AP-Mod's make_meta.py
    # Do not change this without making sure the two folder hashing operations are identical.
    for entry in sorted(file_list, key=lambda entry: entry.name):
        if not entry.exists() or not entry.is_file():
            continue
        source_hash.update(entry.name.encode("utf-8"))

        with open(entry, "rb") as f:
            file_hash = hashlib.file_digest(f, "md5")

        source_hash.update(file_hash.digest())

    return source_hash.hexdigest()


def load_patch(apw_version: str) -> None:
    current_version = KhimeraDAMGStorageHandler.get("version", "meta", category="current_patch")
    loaded_path = KhimeraDAMGStorageHandler.get_path_raw(folder="loaded_patch")

    if current_version is not None and current_version == apw_version and loaded_path.exists():
        current_files: list[str] = KhimeraDAMGStorageHandler.get("files", "meta", category="current_patch")
        current_hash: str = KhimeraDAMGStorageHandler.get("hash", "meta", category="current_patch")

        file_list = [loaded_path / entry for entry in current_files]

        loaded_hash = _hash_multiple_files(file_list)

        if current_hash == loaded_hash:
            # No need to load patch.
            return

    # If we got here we need to load the patch.

    # Cleanup current patch metadata
    KhimeraDAMGStorageHandler.store(key="current_patch", value=None, file_name="meta")

    attempts = 5
    nested_errors = []
    for i in range(attempts):
        if loaded_path.exists():
            try:
                shutil.rmtree(loaded_path)
            except OSError as err:
                nested_errors.append(err)
                if i == attempts - 1:
                    raise OSError(
                        f"Failed to delete {loaded_path}"
                    ) from ExceptionGroup(
                        f"Several attempts to delete {loaded_path} have failed.",
                        nested_errors
                    )
                time.sleep(0.01)  # Small cooldown to wait for any OS blockings to dissipate. Blocks the thread.
                continue
            break
        break

    loaded_path.mkdir()

    sources = source_get(apw_version)
    if len(sources) == 0:
        raise SourceNotFoundError("Could not find a compatible source.")

    # If multiple sources exist, we will use the first available one for now.
    # Maybe in a future update we can have the user set a preferred version, but this is not a priority rn.
    source = sources[0]  # The available source, or itch if both (considering itch comes first alphabetically)
    source_path = KhimeraDAMGStorageHandler.get_path_raw(folder=f"source/{source}")

    patch = get_patch(source_path, apw_version)

    source_files = [entry.name for entry in source_path.iterdir()]
    source_file_paths = [source_path / entry for entry in source_files]
    loaded_file_paths = [loaded_path / entry for entry in source_files]
    for entry in source_file_paths:
        if entry.name == "data.win":
            shutil.copy2(patch, loaded_path / "data.win")
            continue
        if entry.name == "khimera1.exe":
            # Rename executable so we have an unique exe name for ourselves.
            shutil.copy2(entry, loaded_path / executable_name)
            continue
        shutil.copy2(entry, loaded_path)

    source_hash = _hash_multiple_files(loaded_file_paths)

    current_patch_data = {
        "version": apw_version,
        "files": source_files,
        "hash": source_hash
    }

    KhimeraDAMGStorageHandler.store_many(
        list(current_patch_data.keys()),
        list(current_patch_data.values()),
        "meta",
        category="current_patch"
    )

    return


def source_validate(source_path: Path) -> tuple[bool, str | None]:
    if not source_path.exists():
        return (False, None)

    data_path = source_path / "data.win"

    if not data_path.exists():
        return (False, None)

    if data_path.stat().st_size > (max_source_data_size):
        return (False, None)

    try:
        data = data_path.read_bytes()
    except FileNotFoundError:
        # We do not except OSError, as it is not a fault with the Path or the data.
        return (False, None)

    data_hash = hashlib.md5(data).hexdigest()

    build_name = _supported_build_hashes_inverted.get(data_hash)
    if build_name is None:
        return (False, None)

    build = builds[build_name]

    candidate_files = [
        entry
        for entry in source_path.iterdir()
        if entry.name in build.file_names and entry.is_file()
    ]

    total_sum = sum(entry.stat().st_size for entry in candidate_files)

    if total_sum > max_build_size:
        return (False, None)

    source_hash = _hash_multiple_files(candidate_files)

    if source_hash != build.files_hash_id:
        return (False, None)

    return (True, build_name)


# Returns all available source builds. An empty return means there are no builds for this version.
def source_get(apw_version: str, *, build_name: str | None = None, return_any: bool = False) -> list[str]:
    mod_version = _get_mod_version(apw_version)
    build_list = _get_source_map(mod_version).values()
    ret: list[str] = []
    for name in build_list:
        build_path = KhimeraDAMGStorageHandler.get_path_raw(folder=f"source/{name}", skip_mkdir=True)
        if not build_path.exists():
            continue
        if not source_validate(build_path)[0]:
            shutil.rmtree(build_path)
            continue
        if build_name is not None and build_name != name:
            continue
        ret.append(name)
        if return_any:
            return ret

    return ret


def get_valid_builds(apw_version: str) -> list[str]:
    mod_version = _get_mod_version(apw_version)
    ret = _get_source_map(mod_version).values()
    return list(ret)


def try_load_build(candidate_path: Path) -> bool:
    validated, build_name = source_validate(candidate_path)
    if not validated or build_name is None:
        return False

    build = builds[build_name]
    source_path = KhimeraDAMGStorageHandler.get_path_raw(folder=f"source/{build_name}")

    # Check to see if the current loaded build is fine
    validated, old_build_name = source_validate(source_path)
    if validated and build_name == old_build_name:
        # No need to copy, but we need to validate the steam_appid.txt file separately here
        if build_name.startswith("steam"):
            steam_app_id = source_path / "steam_appid.txt"
            if not steam_app_id.exists() or steam_app_id.read_text(encoding="utf-8-sig") != "467380":
                steam_app_id.write_text("467380", encoding="utf-8")
        return True

    if source_path.exists():
        try:
            shutil.rmtree(source_path)
        except OSError as err:
            raise SourceCouldNotBeDeletedError("The existing source folder could not be deleted completely.") from err

    source_path.mkdir(exist_ok=True)

    valid_files = [candidate_path / entry for entry in build.file_names]

    for entry in valid_files:
        shutil.copy2(entry, source_path)

    if build_name.startswith("steam"):
        steam_app_id = source_path / "steam_appid.txt"
        if not steam_app_id.exists() or steam_app_id.read_text(encoding="utf-8-sig") == "467380":
            steam_app_id.write_text("467380", encoding="utf-8")

    return True
