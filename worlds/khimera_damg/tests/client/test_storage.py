# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The client's YAML key/value store, its export/import path, and path containment.

KR-002 lived here: the imported file's own ``id`` field was turned straight into a filesystem
path, so a crafted save could delete or overwrite any ``*.yaml`` file on the machine. The
containment tests below are the regression cover for that, and they check both halves - the
rejection *and* that nothing was written outside the storage folder.

Containment is measured against ``Utils.user_path("khimera_damg")``, not against the subfolder,
so a name that stays inside that root is legitimate even if it leaves ``game_data``.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import yaml

from ...client import dialog
from ...client.client import get_game_id
from ...client.storage import KhimeraDAMGStorageHandler as Storage
from ..support.sandbox import AsyncRedirectedTestCase, RedirectedTestCase

GAME_ID = "0123456789abcdef0123456789abcdef"
OTHER_GAME_ID = "ffffffffffffffffffffffffffffffff"

# Ids that must never be turned into a path. The first group escapes the folder, the rest are
# simply not ids the client ever produces.
MALICIOUS_IDS = [
    "../../host",
    "..\\..\\host",
    "/etc/passwd",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "0123456789abcdef0123456789abcde",       # 31 characters
    "0123456789abcdef0123456789abcdeff",     # 33 characters
    "0123456789ABCDEF0123456789ABCDEF",      # upper case
    "not a game id",
    ""
]


class TestKeyValueStore(RedirectedTestCase):
    """``store``/``get`` and the on-disk layout."""

    def test_round_trip(self) -> None:
        Storage.store("last_ack", 7, GAME_ID, folder="game_data")
        self.assertEqual(Storage.get("last_ack", GAME_ID, 0, folder="game_data"), 7)

    def test_file_lands_in_the_expected_place(self) -> None:
        Storage.store("last_ack", 7, GAME_ID, folder="game_data")
        expected = self.user_root / "khimera_damg" / "game_data" / f"{GAME_ID}.yaml"
        self.assertTrue(
            expected.is_file(),
            f"expected {expected} to exist, found {sorted(path.name for path in self.user_root.rglob('*'))}"
        )

    def test_no_temporary_file_is_left_behind(self) -> None:
        Storage.store("last_ack", 7, GAME_ID, folder="game_data")
        strays = list((self.user_root / "khimera_damg" / "game_data").glob("*.tmp"))
        self.assertEqual(strays, [], f"the atomic write left {strays} behind")

    def test_categories_are_separate(self) -> None:
        Storage.store("key", "in category", GAME_ID, "game_data", folder="game_data")
        self.assertIsNone(
            Storage.get("key", GAME_ID, None, folder="game_data"),
            "a categorised value leaked into the top level"
        )
        self.assertEqual(Storage.get("key", GAME_ID, None, "game_data", folder="game_data"), "in category")

    def test_whole_category_can_be_read(self) -> None:
        Storage.store_many(["a", "b"], [1, 2], GAME_ID, "game_data", folder="game_data")
        self.assertEqual(Storage.get("game_data", GAME_ID, {}, folder="game_data"), {"a": 1, "b": 2})

    def test_storing_none_removes_the_key(self) -> None:
        Storage.store("key", 1, GAME_ID, folder="game_data")
        Storage.store("key", None, GAME_ID, folder="game_data")
        self.assertEqual(
            Storage.get("key", GAME_ID, "gone", folder="game_data"),
            "gone",
            "storing None should remove the key"
        )

    def test_storing_none_removes_a_categorised_key(self) -> None:
        Storage.store("key", 1, GAME_ID, "game_data", folder="game_data")
        Storage.store("key", None, GAME_ID, "game_data", folder="game_data")
        self.assertEqual(Storage.get("key", GAME_ID, "gone", "game_data", folder="game_data"), "gone")

    def test_store_many_rejects_mismatched_lengths(self) -> None:
        with self.assertRaises(ValueError):
            Storage.store_many(["a", "b"], [1], GAME_ID, folder="game_data")

    def test_id_is_always_the_file_name(self) -> None:
        Storage.store("key", 1, GAME_ID, folder="game_data")
        self.assertEqual(
            Storage.get("id", GAME_ID, None, folder="game_data"),
            GAME_ID,
            "the stored document must carry its own id, which the importer reads back"
        )

    def test_unreadable_content_is_discarded_rather_than_raised(self) -> None:
        path = Storage._get_path(GAME_ID, "game_data")
        path.write_text("- this is a list, not a mapping\n", encoding="utf-8")
        self.assertEqual(
            Storage.get("key", GAME_ID, "default", folder="game_data"),
            "default",
            "a file holding the wrong YAML shape should read as empty"
        )

    def test_store_as_file_writes_bytes_and_text(self) -> None:
        binary = Storage.store_as_file(b"\x00\x01\x02", "blob.bin", folder="patches")
        text = Storage.store_as_file("hello", "note.txt", folder="patches")
        self.assertEqual(binary.read_bytes(), b"\x00\x01\x02")
        self.assertEqual(text.read_text(encoding="utf-8"), "hello")
        strays = list(binary.parent.glob("*.tmp"))
        self.assertEqual(strays, [], f"store_as_file left {strays} behind")


class TestPathContainment(RedirectedTestCase):
    """Nothing derived from a file name may resolve outside the storage root (KR-002)."""

    def test_folder_traversal_is_rejected(self) -> None:
        for folder in ("..", "../..", "..\\..", "game_data/../.."):
            with self.subTest(folder=folder):
                with self.assertRaises(ValueError, msg=f"folder \"{folder}\" was accepted"):
                    Storage._get_path("file", folder)

    def test_file_traversal_is_rejected(self) -> None:
        for file_name in ("../../host", "..\\..\\host", "../../../host"):
            with self.subTest(file_name=file_name):
                with self.assertRaises(ValueError, msg=f"file name \"{file_name}\" was accepted"):
                    Storage._get_path(file_name, "game_data")

    def test_absolute_file_name_is_rejected(self) -> None:
        outside = (self.outside_root / "escaped").as_posix()
        with self.assertRaises(ValueError, msg=f"absolute file name \"{outside}\" was accepted"):
            Storage._get_path(outside, "game_data")

    def test_raw_paths_are_contained_too(self) -> None:
        # get_path_raw is what the patcher uses for the source, patch and loaded_patch folders.
        with self.assertRaises(ValueError):
            Storage.get_path_raw("file", "..")
        with self.assertRaises(ValueError):
            Storage.get_path_raw("../../file", "patches")

    def test_a_name_inside_the_root_is_still_allowed(self) -> None:
        # Leaving game_data but staying under khimera_damg is not an escape, and the patcher
        # relies on being able to address sibling folders.
        path = Storage.get_path_raw("../patches", "source")
        self.assertTrue(path.is_relative_to(Path(self.user_root / "khimera_damg")))

    def test_rejection_writes_nothing_outside(self) -> None:
        decoy = self.user_root / "decoy.yaml"
        decoy.write_text("keep me\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            Storage.store("key", "value", "../../decoy", folder="game_data")
        self.assertEqual(
            decoy.read_text(encoding="utf-8"),
            "keep me\n",
            f"{decoy} was modified, so a write escaped the storage root"
        )


class TestWipeAndDelete(RedirectedTestCase):
    """``wipe`` clears the save folder but spares the game that is still loaded."""

    def setUp(self) -> None:
        super().setUp()
        Storage.store("key", 1, GAME_ID, folder="game_data")
        Storage.store("key", 2, OTHER_GAME_ID, folder="game_data")
        self.game_data = self.user_root / "khimera_damg" / "game_data"

    def test_wipe_keeps_the_exception(self) -> None:
        Storage.wipe(GAME_ID)
        remaining = sorted(path.name for path in self.game_data.iterdir())
        self.assertEqual(
            remaining,
            [f"{GAME_ID}.yaml"],
            f"wipe left {remaining}, expected only the excluded game's file"
        )

    def test_wipe_without_exception_clears_everything(self) -> None:
        Storage.wipe(None)
        remaining = sorted(path.name for path in self.game_data.iterdir())
        self.assertEqual(remaining, [], f"wipe left {remaining}")

    def test_wipe_spares_in_flight_temporary_files(self) -> None:
        stray = self.game_data / f"{OTHER_GAME_ID}.yaml.tmp"
        stray.write_text("half written", encoding="utf-8")
        Storage.wipe(GAME_ID)
        self.assertTrue(stray.exists(), "wipe deleted a .tmp file that another write may still own")

    def test_probe_and_delete(self) -> None:
        self.assertTrue(Storage.probe_data(GAME_ID))
        self.assertTrue(Storage.delete_data(GAME_ID))
        self.assertFalse(Storage.probe_data(GAME_ID))
        self.assertTrue(Storage.delete_data(GAME_ID), "deleting an absent file should still report success")


class TestImport(RedirectedTestCase):
    """``probe_load``/``load_data``: the only path where a file from outside is trusted."""

    def write_export(self, game_id: object, name: str = "export.kdamgdata") -> Path:
        path = self.outside_root / name
        path.write_text(yaml.dump({"id": game_id, "game_data": {"level": 3}}), encoding="utf-8")
        return path

    def test_probe_reports_an_existing_target(self) -> None:
        Storage.store("key", 1, GAME_ID, folder="game_data")
        path = self.write_export(GAME_ID)
        self.assertEqual(Storage.probe_load(str(path)), GAME_ID)

    def test_probe_reports_a_missing_target_as_empty(self) -> None:
        path = self.write_export(GAME_ID)
        self.assertEqual(
            Storage.probe_load(str(path)),
            "",
            "an import with no existing save must report an empty id, not None"
        )

    def test_probe_handles_cancelled_dialogs(self) -> None:
        # Utils.askopenfilename returns "" when the user cancels; None is the no-file case.
        self.assertIsNone(Storage.probe_load(None))
        self.assertIsNone(Storage.probe_load(""))

    def test_load_handles_cancelled_dialogs(self) -> None:
        self.assertFalse(Storage.load_data(None))
        self.assertFalse(Storage.load_data(""))

    def test_malicious_ids_are_rejected(self) -> None:
        for game_id in MALICIOUS_IDS:
            with self.subTest(game_id=game_id):
                path = self.write_export(game_id)
                self.assertIsNone(
                    Storage.probe_load(str(path)),
                    f"probe_load accepted the id \"{game_id}\""
                )
                self.assertFalse(
                    Storage.load_data(str(path)),
                    f"load_data accepted the id \"{game_id}\""
                )

    def test_a_traversing_id_writes_nothing(self) -> None:
        # "../../host" from game_data would land exactly here if the id reached the filesystem.
        decoy = self.user_root / "host.yaml"
        decoy.write_text("keep me\n", encoding="utf-8")
        path = self.write_export("../../host")
        self.assertFalse(Storage.load_data(str(path)))
        self.assertEqual(
            decoy.read_text(encoding="utf-8"),
            "keep me\n",
            f"{decoy} was overwritten by an import; the id reached the filesystem"
        )

    def test_non_mapping_payload_is_rejected(self) -> None:
        path = self.outside_root / "list.kdamgdata"
        path.write_text("- 1\n- 2\n", encoding="utf-8")
        self.assertIsNone(Storage.probe_load(str(path)))
        self.assertFalse(Storage.load_data(str(path)))

    def test_binary_payload_is_rejected(self) -> None:
        # A non-UTF-8 file raises UnicodeDecodeError on read; it has to be handled, not propagated.
        path = self.outside_root / "binary.kdamgdata"
        path.write_bytes(b"\xff\xfe\x00\x01not text at all")
        self.assertIsNone(Storage.probe_load(str(path)))
        self.assertFalse(Storage.load_data(str(path)))

    def test_valid_import_replaces_the_save(self) -> None:
        Storage.store("level", 1, GAME_ID, "game_data", folder="game_data")
        path = self.write_export(GAME_ID)
        self.assertTrue(Storage.load_data(str(path)))
        self.assertEqual(
            Storage.get("level", GAME_ID, None, "game_data", folder="game_data"),
            3,
            "the imported file did not replace the stored save"
        )

    def test_valid_import_creates_a_missing_save(self) -> None:
        path = self.write_export(GAME_ID)
        self.assertTrue(Storage.load_data(str(path)))
        self.assertTrue(Storage.probe_data(GAME_ID))

    def test_game_ids_look_like_the_accepted_shape(self) -> None:
        # The importer only accepts 32 lowercase hex characters, which is what get_game_id makes.
        produced = get_game_id("Tester", "12345678901234567890")
        self.assertRegex(produced, r"^[0-9a-f]{32}$")
        self.assertNotEqual(
            produced,
            get_game_id("Tester", "09876543210987654321"),
            "two seeds produced the same game id"
        )
        self.assertNotEqual(
            produced,
            get_game_id("Other", "12345678901234567890"),
            "two slots produced the same game id"
        )


class TestExport(AsyncRedirectedTestCase):
    """``save_data`` copies a save out through a file dialog."""

    async def test_export_copies_the_save(self) -> None:
        Storage.store("level", 3, GAME_ID, "game_data", folder="game_data")
        destination = self.outside_root / "exported.kdamgdata"
        with mock.patch.object(dialog, "run", mock.AsyncMock(return_value=str(destination))):
            self.assertTrue(await Storage.save_data(GAME_ID))
        self.assertIn("level", destination.read_text(encoding="utf-8"))

    async def test_export_of_a_missing_save_fails_before_prompting(self) -> None:
        with mock.patch.object(dialog, "run", mock.AsyncMock(return_value="never used")) as prompt:
            self.assertFalse(await Storage.save_data(GAME_ID))
        prompt.assert_not_called()

    async def test_cancelled_export_reports_failure(self) -> None:
        Storage.store("level", 3, GAME_ID, "game_data", folder="game_data")
        for cancelled in (None, ""):
            with self.subTest(dialog_result=cancelled):
                with mock.patch.object(dialog, "run", mock.AsyncMock(return_value=cancelled)):
                    self.assertFalse(await Storage.save_data(GAME_ID))
