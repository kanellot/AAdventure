"""Pruebas unitarias para el empaquetador de aventuras (adventure_packager)."""

import os
import shutil
import tempfile
import unittest
import zipfile
import json
from adventure_packager import AdventurePackager


class TestAdventurePackager(unittest.TestCase):
    """Pruebas del empaquetado, desempaquetado y validación de contenedores .aad."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="packager_test_")
        self.aad_path = os.path.join(self.temp_dir, "test_adventure.aad")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pack_creates_valid_zip_with_six_files(self):
        world_data = {"world": {"id": "w1", "name": "Mundo", "locations": []}}
        npcs_data = {"npcs": []}
        player_data = {"player": {"id": "p1", "name": "Héroe"}}

        AdventurePackager.pack(
            output_path=self.aad_path,
            world_data=world_data,
            npcs_data=npcs_data,
            player_data=player_data,
        )

        self.assertTrue(os.path.exists(self.aad_path))

        # Verificar que es un ZIP con los 6 archivos exactos
        with zipfile.ZipFile(self.aad_path, "r") as z:
            names = set(z.namelist())
            expected = {
                "world.json",
                "npcs.json",
                "player.json",
                "objects.json",
                "loreblocks.json",
                "story_config.json",
            }
            self.assertEqual(names, expected)

            # Verificar contenido por defecto de story_config.json
            with z.open("story_config.json") as sc:
                cfg_dict = json.loads(sc.read().decode("utf-8"))
                self.assertTrue(cfg_dict.get("affinity"))
                self.assertTrue(cfg_dict.get("elapsed_time"))
                self.assertTrue(cfg_dict.get("fog_war"))

    def test_unpack_to_temp(self):
        # Empaquetar primero
        AdventurePackager.pack(
            output_path=self.aad_path,
            world_data={"world": {}},
            npcs_data={"npcs": []},
            player_data={"player": {}},
            objects_data={"objects": []},
            lore_data={"lore_blocks": []},
            config_data={"fog_war": True},
        )

        unpacked_dir = AdventurePackager.unpack_to_temp(self.aad_path)
        try:
            self.assertTrue(os.path.isdir(unpacked_dir))
            for fn in ["world.json", "npcs.json", "player.json", "objects.json", "loreblocks.json", "story_config.json"]:
                self.assertTrue(os.path.exists(os.path.join(unpacked_dir, fn)))
        finally:
            shutil.rmtree(unpacked_dir, ignore_errors=True)

    def test_unpack_nonexistent_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            AdventurePackager.unpack_to_temp("ruta/inexistente/aventura.aad")


if __name__ == "__main__":
    unittest.main()
