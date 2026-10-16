# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""What ships, and whether the two sides of the protocol still speak the same language.

Three things are checked here:

* the test package is excluded from the built ``.apworld`` by ``.apignore``;
* every file the world references at run time exists;
* the patch zips use ``/`` in their entry names (KR-023) and the mod reads the field names the
  client writes (KR-009, KR-020).

The mod lives in a submodule, so the parity test skips when it is not checked out.
"""

from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from Utils import read_apignore  # type: ignore
from worlds.LauncherComponents import icon_paths  # type: ignore

from ... import GAME_ID, KhimeraDAMGWorld

WORLD_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = WORLD_ROOT.parents[1]
MOD_CODE = REPO_ROOT / "KhimeraDAMG-AP-Mod" / "code"

# Keys the client writes and the mod has to look up. KR-009 was "data_acks" being read as
# "data_ack"; KR-020 was "generation_information" being read as "generation_info".
SHARED_FIELD_NAMES = [
    # ap.cctx, meta
    "archipelago_version",
    "host_world_version",
    "client_world_version",
    "slot_name",
    "seed",
    "options",
    "generation_information",
    # ap.cctx, session
    "last_ack",
    "item_list",
    "location_ids",
    "is_win",
    "game_data",
    # ap.hi
    "messages",
    "death_link",
    "death_ack",
    "data_acks",
    # ap.li
    "location_classifications",
    "player_ids"
]


class TestApIgnore(unittest.TestCase):
    """The tests must not reach a player's installation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = read_apignore(WORLD_ROOT / ".apignore")

    def test_apignore_exists_and_parses(self) -> None:
        self.assertIsNotNone(
            self.spec,
            f"{WORLD_ROOT / '.apignore'} is empty or unreadable, so the tests would be packaged"
        )

    def test_the_test_package_is_excluded(self) -> None:
        for candidate in (
            "tests/__init__.py",
            "tests/bases.py",
            "tests/support/sandbox.py",
            "tests/generation/test_items.py",
            "tests/guards/test_packaging.py"
        ):
            with self.subTest(path=candidate):
                self.assertTrue(
                    self.spec.match_file(candidate),
                    f"\"{candidate}\" is not excluded by .apignore and would ship inside the .apworld"
                )

    def test_the_world_itself_is_not_excluded(self) -> None:
        for candidate in ("__init__.py", "items.py", "client/client.py", "patches/data.py"):
            with self.subTest(path=candidate):
                self.assertFalse(
                    self.spec.match_file(candidate),
                    f"\"{candidate}\" is excluded by .apignore but has to ship"
                )


class TestReferencedFiles(unittest.TestCase):
    """Everything the world points at has to exist in the package."""

    def test_the_client_icon_exists(self) -> None:
        self.assertIn(GAME_ID, icon_paths, "the client component registered no icon")
        reference = icon_paths[GAME_ID]
        self.assertTrue(reference.startswith("ap:"), f"icon reference \"{reference}\" is not an apworld path")
        relative = reference.split("/", 1)[1]
        self.assertTrue(
            (WORLD_ROOT / relative).is_file(),
            f"the icon reference points at {relative}, which does not exist"
        )

    def test_tutorial_documents_exist(self) -> None:
        for tutorial in KhimeraDAMGWorld.web.tutorials:
            with self.subTest(tutorial=tutorial.tutorial_name):
                self.assertTrue(
                    (WORLD_ROOT / "docs" / tutorial.file_name).is_file(),
                    f"tutorial \"{tutorial.tutorial_name}\" points at docs/{tutorial.file_name}, "
                    "which does not exist"
                )

    def test_the_game_info_page_exists(self) -> None:
        # WebHost looks for en_<game name>.md next to the setup guide.
        expected = WORLD_ROOT / "docs" / f"en_{KhimeraDAMGWorld.game.replace(':', '')}.md"
        self.assertTrue(expected.is_file(), f"the game info page {expected.name} does not exist")


class TestPatchArchives(unittest.TestCase):
    """KR-023: zip entries must use forward slashes, or the patcher fails off Windows."""

    def setUp(self) -> None:
        self.archives = sorted((WORLD_ROOT / "patches").glob("*.zip"))
        if not self.archives:
            self.skipTest("no patch archives present; they are copied in by the build")

    def test_entries_use_forward_slashes(self) -> None:
        for archive in self.archives:
            with zipfile.ZipFile(archive) as handle:
                names = handle.namelist()
            offenders = [name for name in names if "\\" in name]
            self.assertEqual(
                offenders,
                [],
                f"{archive.name} stores {offenders} with backslashes; zip requires \"/\" and the "
                "patcher's lookup fails on Linux and macOS"
            )

    def test_every_build_folder_holds_a_diff(self) -> None:
        for archive in self.archives:
            with zipfile.ZipFile(archive) as handle:
                names = handle.namelist()
            diffs = [name for name in names if name.endswith("kdamg_diff.bsdiff4")]
            self.assertTrue(diffs, f"{archive.name} holds no bsdiff4 patch files, only {names}")


@unittest.skipUnless(MOD_CODE.is_dir(), "the game-side mod submodule is not checked out")
class TestModFieldParity(unittest.TestCase):
    """The mod has to read the names the client writes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(MOD_CODE.glob("*.gml"))
        )

    def test_mod_sources_were_found(self) -> None:
        self.assertGreater(len(self.sources), 0, f"no .gml sources were read from {MOD_CODE}")

    def test_every_shared_field_is_read_by_the_mod(self) -> None:
        for field in SHARED_FIELD_NAMES:
            with self.subTest(field=field):
                self.assertIn(
                    f"\"{field}\"",
                    self.sources,
                    f"the client writes \"{field}\" but no mod source looks it up; a renamed key on "
                    "either side is silently ignored at run time"
                )
