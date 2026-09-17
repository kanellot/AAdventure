"""Pruebas unitarias para la persistencia de preferencias de aventuras."""

import unittest
import os
import tempfile
from unittest.mock import patch
from adventure_selector.storage import (
    load_preferences,
    save_preferences,
    get_default_adventure_path,
    set_default_adventure_path,
    get_recent_adventures,
)


class TestAdventureStorage(unittest.TestCase):
    """Verifica el guardado y recuperación de preferencias del selector."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.prefs_file = os.path.join(self.temp_dir.name, "test_prefs.json")
        self.patcher = patch("adventure_selector.storage.PREFERENCES_FILE_PATH", self.prefs_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_default_preferences_when_empty(self):
        prefs = load_preferences()
        self.assertIsNone(prefs.get("last_selected_aad"))
        self.assertEqual(prefs.get("recent_adventures"), [])

    def test_save_and_load_preferences(self):
        data = {
            "last_selected_aad": "C:/fake/path.aad",
            "recent_adventures": ["C:/fake/path.aad"],
        }
        save_preferences(data)
        loaded = load_preferences()
        self.assertEqual(loaded["last_selected_aad"], "C:/fake/path.aad")
        self.assertEqual(len(loaded["recent_adventures"]), 1)

    def test_set_and_get_default_adventure(self):
        # Crear un archivo ficticio que exista físicamente
        real_temp_aad = os.path.join(self.temp_dir.name, "MyAdventure.aad")
        with open(real_temp_aad, "w", encoding="utf-8") as f:
            f.write("dummy")

        set_default_adventure_path(real_temp_aad)
        default_path = get_default_adventure_path()
        self.assertEqual(default_path, os.path.abspath(real_temp_aad))

        recents = get_recent_adventures()
        self.assertIn(os.path.abspath(real_temp_aad), recents)


if __name__ == "__main__":
    unittest.main()
