"""Pruebas unitarias para las reglas de validación de historias en EditorController."""

import unittest
from editor.controller import EditorController
from domains import Player, World, Location, Place


class TestStoryValidation(unittest.TestCase):
    """Verifica el cumplimiento de las restricciones de integridad antes de exportar a .aad."""

    def setUp(self):
        self.controller = EditorController()
        self.controller.new_story()

    def test_valid_story_passes(self):
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_missing_player_fails(self):
        self.controller.player = None
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("No se ha definido el jugador", err)

    def test_empty_initial_place_fails(self):
        self.controller.player.initial_place = ""
        self.controller.player.player_location = ""
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("lugar de inicio", err)

    def test_empty_world_places_fails(self):
        self.controller.world.locations.clear()
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("al menos un lugar definido", err)

    def test_nonexistent_initial_place_fails(self):
        self.controller.player.initial_place = "lugar_inexistente"
        self.controller.player.player_location = "lugar_inexistente"
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("no existe en el mundo", err)

    def test_save_invalid_story_raises_value_error(self):
        self.controller.player = None
        with self.assertRaises(ValueError):
            self.controller.save_story("should_fail.aad")


if __name__ == "__main__":
    unittest.main()
