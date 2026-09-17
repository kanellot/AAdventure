"""Pruebas unitarias para EditorController: carga, mutación y guardado en .aad."""

import unittest
import os
import tempfile
from editor.controller import EditorController
from domains import LoreBlock


class TestEditorController(unittest.TestCase):
    """Verifica el ciclo de vida, mutaciones en memoria y persistencia del editor."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.controller = EditorController()

    def test_new_story(self):
        self.controller.new_story()
        self.assertIsNotNone(self.controller.world)
        self.assertIsNotNone(self.controller.player)
        self.assertEqual(len(self.controller.world.locations), 1)
        self.assertEqual(len(self.controller.get_all_places()), 1)
        self.assertTrue(bool(self.controller.player.initial_place))

        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_load_canonical_story(self):
        self.controller.load_story(self.aad_path)
        self.assertIsNotNone(self.controller.world)
        self.assertGreater(len(self.controller.get_all_places()), 0)
        self.assertGreater(len(self.controller.npcs), 0)
        self.assertIsNotNone(self.controller.player)
        self.assertGreater(len(self.controller.lore_blocks), 0)

    def test_entity_mutations_and_save_cycle(self):
        self.controller.load_story(self.aad_path)

        # 1. Agregar nueva localización y lugar
        loc = self.controller.add_location("Bosque Oscuro", "Un bosque sombrío.")
        new_place = self.controller.add_place(loc.id, "Claro del Bosque", "Un claro iluminado por la luna.")
        self.assertIsNotNone(new_place)

        # 2. Agregar nuevo NPC
        new_npc = self.controller.add_npc("Druida Silvano", "Un anciano protector del bosque.", initial_place=new_place.id)
        self.assertIn(new_npc, self.controller.npcs)

        # 3. Agregar nuevo LoreBlock
        new_lb = LoreBlock(
            id="lb_bosque_secreto",
            title="El Secreto del Bosque",
            directive="Revela pistas del bosque.",
        )
        self.controller.add_lore_block(new_lb)

        # 4. Guardar a un archivo .aad temporal y verificar re-carga
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_aad = os.path.join(temp_dir, "SavedStory.aad")
            self.controller.save_story(temp_aad)
            self.assertTrue(os.path.exists(temp_aad))

            # Crear un nuevo controlador y cargar el .aad guardado
            verifier_controller = EditorController()
            verifier_controller.load_story(temp_aad)

            self.assertIsNotNone(verifier_controller.get_place_by_name("Claro del Bosque"))
            self.assertTrue(any(n.name == "Druida Silvano" for n in verifier_controller.npcs))
            self.assertTrue(any(lb.id == "lb_bosque_secreto" for lb in verifier_controller.lore_blocks))

    def test_remove_npc(self):
        self.controller.load_story(self.aad_path)
        npc = self.controller.add_npc("Guardaespaldas", "Fuerte y silencioso.")
        self.assertIn(npc, self.controller.npcs)

        removed = self.controller.remove_npc(npc.id)
        self.assertTrue(removed)
        self.assertNotIn(npc, self.controller.npcs)


if __name__ == "__main__":
    unittest.main()
