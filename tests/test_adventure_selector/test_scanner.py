"""Pruebas unitarias para el escáner de paquetes de aventura."""

import unittest
import os
import tempfile
import zipfile
from adventure_selector.scanner import scan_adventures


class TestAdventureScanner(unittest.TestCase):
    """Verifica el escaneo y catalogación de archivos .aad en el sistema."""

    def test_scan_default_directories(self):
        results = scan_adventures()
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)

        names = [r.file_name for r in results]
        self.assertIn("Adventure.aad", names)

    def test_scan_extra_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear un archivo dummy .aad
            dummy_aad = os.path.join(temp_dir, "CustomTest.aad")
            with zipfile.ZipFile(dummy_aad, "w") as zf:
                zf.writestr("world.json", '{"name": "Custom World"}')

            # Crear un archivo no aad
            ignored_file = os.path.join(temp_dir, "ignored.txt")
            with open(ignored_file, "w", encoding="utf-8") as f:
                f.write("test")

            results = scan_adventures(extra_directories=[temp_dir])
            file_names = [r.file_name for r in results]

            self.assertIn("CustomTest.aad", file_names)
            self.assertNotIn("ignored.txt", file_names)


if __name__ == "__main__":
    unittest.main()
