"""Pruebas unitarias para el lector de metadatos de aventuras (.aad)."""

import unittest
import os
import tempfile
from adventure_selector.reader import read_adventure_metadata
from adventure_selector.models import AdventureMetadata


class TestAdventureReader(unittest.TestCase):
    """Verifica la inspección y extracción de metadatos de paquetes .aad."""

    def test_read_valid_adventure(self):
        canonical_aad = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(canonical_aad):
            self.skipTest("Adventure.aad no existe en el entorno de prueba")

        meta = read_adventure_metadata(canonical_aad)
        self.assertIsInstance(meta, AdventureMetadata)
        self.assertTrue(meta.is_valid)
        self.assertEqual(meta.file_name, "Adventure.aad")
        self.assertGreater(meta.file_size_kb, 0.0)
        self.assertTrue(bool(meta.title))
        self.assertTrue(bool(meta.player_name))
        self.assertGreaterEqual(meta.places_count, 1)
        self.assertGreaterEqual(meta.npcs_count, 1)

    def test_read_nonexistent_file(self):
        meta = read_adventure_metadata("non_existent_file_path.aad")
        self.assertFalse(meta.is_valid)
        self.assertIn("no existe", meta.error_message)

    def test_read_corrupted_zip_file(self):
        with tempfile.NamedTemporaryFile(suffix=".aad", delete=False) as tf:
            tf.write(b"NOT A VALID ZIP ARCHIVE")
            bad_path = tf.name

        try:
            meta = read_adventure_metadata(bad_path)
            self.assertFalse(meta.is_valid)
            self.assertTrue(bool(meta.error_message))
        finally:
            if os.path.exists(bad_path):
                os.unlink(bad_path)


if __name__ == "__main__":
    unittest.main()
