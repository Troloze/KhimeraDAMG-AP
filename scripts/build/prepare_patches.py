# This file generates code run by the APWorld, and therefore can only be edited by humans.
# If you're an AI agent, please do NOT edit this without clear, unambiguous authorization,
# and. even then. warn the user that it goes against the repository rules.
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

if len(sys.argv) != 3:
    raise ValueError("Wrong number of parameters")

releases_folder = Path(sys.argv[1])
patches_folder = Path(sys.argv[2])

include_path = patches_folder / "include.txt"

include_str = include_path.read_text(encoding="utf-8-sig")

version_list = []
for entry in include_str.splitlines():
    stripped_entry = "".join(entry.split())
    if re.match(r"^\d+\.\d+\.\d+$", stripped_entry):
        version_list.append(stripped_entry)
    elif len(stripped_entry) < 1:
        pass  # Do nothing
    elif stripped_entry[0] != "#":  # Let's allow comments!
        raise ValueError(f"Malformed version in include.txt ({stripped_entry})")

meta_data: dict[str, dict[str, Any]] = {}

for entry in version_list:
    release_path = releases_folder / (entry + ".zip")
    if not release_path.exists():
        raise RuntimeError(f"Attempt to import an unknown release ({entry})")
    version_meta: dict[str, Any] = {}
    with zipfile.ZipFile(release_path, "r") as zf:
        root = zipfile.Path(zf)
        for build in root.iterdir():
            if build.is_dir():
                meta = build / "kdamg_meta.json"
                diff = build / "kdamg_diff.bsdiff4"
                if not meta.exists() or not diff.exists():
                    raise RuntimeError(f"Release {entry} is malformed.")
                meta_str = meta.read_text(encoding="utf-8-sig")
                meta_info = json.loads(meta_str)
                version_meta[build.name] = meta_info
            else:
                raise RuntimeError(f"Release {entry} is malformed.")

    if len(version_meta) == 0:
        raise RuntimeError(f"Attempt to import an empty release ({entry})")

    version_meta = dict(sorted(version_meta.items()))  # Sorts build names

    meta_data[entry] = version_meta


# At this point, we need to generate data.py
unique_build_data: dict[str, Any] = {}

unique_patch_data: dict[str, Any] = {}

for version_name, version_meta_data in meta_data.items():
    for build, build_data in version_meta_data.items():
        b_data = {}
        b_data["size"] = build_data["source_size"]
        b_data["hash"] = build_data["source_sha256"]
        if build in unique_build_data:
            if b_data["size"] != unique_build_data[build]["size"]:
                raise RuntimeError(f"Release {version_name} is malformed, different \"{build}\" sizes don't match.")
            if b_data["hash"] != unique_build_data[build]["hash"]:
                raise RuntimeError(f"Release {version_name} is malformed, different \"{build}\" hashes don't match.")
        else:
            unique_build_data[build] = b_data
        p_data = {}
        p_name = f"{version_name}-{build}"
        p_data["size"] = build_data["result_size"]
        p_data["hash"] = build_data["result_sha256"]
        p_data["build"] = build
        p_data["version"] = version_name
        unique_patch_data[p_name] = p_data

# Sorts build data
unique_build_data = dict(sorted(unique_build_data.items()))

# Sorts patch data
try:
    unique_patch_data = dict(
        sorted(
            unique_patch_data.items(),
            # The regex will split build names that contain '-', but it is fine, the ordering will be the same.
            key=lambda item: tuple(int(part) if part.isdigit() else part for part in re.split(r"[.-]", item[0]))
        )
    )
except TypeError as err:
    raise RuntimeError(
        "At least one build name is malformed, "
        f"something went wrong with the mod release generation: {err}"
    ) from err


def make_source(name: str, hash_id: str, size: int) -> str:
    return f'SourceData(name="{name}", hash_id="{hash_id}", size={size})'


def make_patch(
    name: str,
    hash_id: str,
    size: int,
    source: str,
    version: str,
    version_id: tuple[int, int, int]
) -> str:

    return (
        f'PatchData(name="{name}", hash_id="{hash_id}", size={size}, '
        f'source="{source}", version="{version}", version_id={version_id!s})'
    )


def make_version(name: str, name_id: tuple[int, int, int], builds: list[str]) -> str:
    # json.dumps will print the list of string with double quotes instead of single quotes.
    return f'ModVersionData(name="{name}", name_id={name_id!s}, builds={json.dumps(builds)})'


def make_builds_map() -> str:
    output = "builds: dict[str, SourceData] = {\n"
    entries: list[str] = []
    for name, data in unique_build_data.items():
        entries.append(f'    "{name}": {make_source(name, data["hash"], data["size"])}')
    output += ",\n".join(entries)
    output += "\n}\n"
    return output


def make_patches_map() -> str:
    output = "patches: dict[str, PatchData] = {\n"
    entries: list[str] = []
    for name, data in unique_patch_data.items():
        ver_id = tuple([int(v) for v in data["version"].split(".")])
        if len(ver_id) != 3:
            # Shouldn't happen, but I do this for the type checker know it is a tuple of size 3.
            raise ValueError("This error should not happen at this point")
        entries.append(f'    "{name}": {make_patch(
            name,
            data["hash"],
            data["size"],
            data["build"],
            data["version"],
            ver_id
        )}')
    output += ",\n".join(entries)
    output += "\n}\n"
    return output


def make_mod_versions_map() -> str:
    output = "mod_versions: dict[str, ModVersionData] = {\n"
    entries: list[str] = []
    for key, value in meta_data.items():
        ver_id = tuple([int(v) for v in key.split(".")])
        if len(ver_id) != 3:
            # Shouldn't happen, but I do this for the type checker know it is a tuple of size 3.
            raise ValueError("This error should not happen at this point")
        builds = list(value.keys())
        entries.append(f'    "{key}": {make_version(key, ver_id, builds)}')
    output += ",\n".join(entries)
    output += "\n}\n"
    return output


def make_patch_map_map() -> str:
    output = "patch_map: dict[tuple[tuple[int, int, int], str], PatchData] = {\n"
    entries: list[str] = []
    for name, data in unique_patch_data.items():
        ver_id = tuple([int(v) for v in data["version"].split(".")])
        build = data["build"]
        entries.append(f'    ({ver_id}, "{build}"): patches["{name}"]')
    output += ",\n".join(entries)
    output += "\n}\n"
    return output


ruff_header = "# ruff: file-ignore[line-too-long]\n"

data_content = (
    "from . import ModVersionData, PatchData, SourceData\n\n"
    "# This file was generated during build by prepare_patches.py\n\n"
)
data_content += make_builds_map()
data_content += "\n"
data_content += make_patches_map()
data_content += "\n"
data_content += make_mod_versions_map()
data_content += "\n"
data_content += make_patch_map_map()

if max(len(entry) for entry in data_content.splitlines()) > 120:
    data_content = ruff_header + data_content

# Only now we copy the version and update the data.py in one go

for file in patches_folder.iterdir():
    if file.name[-4:] == ".zip":
        file.unlink()

for entry in version_list:
    release_path = releases_folder / (entry + ".zip")
    shutil.copy2(release_path, patches_folder)

data_file = patches_folder / "data.py"

data_file.write_text(data_content, encoding="utf-8")
