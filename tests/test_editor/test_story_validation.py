"""Pruebas unitarias para las reglas de validación de historias en EditorController."""

import os
import tempfile
import unittest
from editor_debugger.editor.controller import EditorController
from domains import Player, World, Location, Place, NPC, Item, Connection


class TestStoryValidation(unittest.TestCase):
    """Verifica el cumplimiento de las restricciones de integridad antes de exportar a .aad."""

    def setUp(self):
        self.controller = EditorController()
        self.controller.new_story()

    def test_valid_default_story_passes(self):
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    # 1. Reglas de mínimo estructural
    def test_missing_world_fails(self):
        self.controller.world = None
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("Mundo", err)

    def test_missing_locations_fails(self):
        self.controller.world.locations.clear()
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("Localización", err)

    def test_missing_places_fails(self):
        self.controller.world.locations[0].places.clear()
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("al menos un lugar definido", err)

    def test_missing_player_fails(self):
        self.controller.player = None
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("No se ha definido el jugador", err)

    # 2. Validación de Player initial_location
    def test_empty_player_location_fails(self):
        self.controller.player.initial_location = ""
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("initial_location", err)

    def test_nonexistent_player_location_fails(self):
        self.controller.player.initial_location = "lugar_inexistente"
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("no existe en el mundo", err)

    # 3. Validación de NPC initial_location
    def test_npc_without_location_fails(self):
        self.controller.add_npc("Tabernero", "Sirve bebidas", initial_location=None)
        self.controller.npcs[-1].initial_location = ""
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("Tabernero", err)
        self.assertIn("initial_location", err)

    def test_npc_with_nonexistent_location_fails(self):
        self.controller.add_npc("Tabernero", "Sirve bebidas", initial_location="lugar_fantasma")
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("no existe en el mundo", err)

    def test_npc_with_valid_location_passes(self):
        place = self.controller.get_all_places()[0]
        self.controller.add_npc("Tabernero", "Sirve bebidas", initial_location=place.id)
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    # 4. Validación de Item initial_location / inventario
    def test_item_without_location_and_not_in_inventory_fails(self):
        self.controller.add_item("Espada", "Una espada de hierro", initial_location=None)
        self.controller.items[-1].initial_location = ""
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("Espada", err)
        self.assertIn("inventario", err)

    def test_item_in_player_inventory_passes(self):
        item = self.controller.add_item("Espada", "Una espada de hierro", initial_location=None)
        item.initial_location = ""
        self.controller.player.inventory.append(item.id)
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_item_with_valid_place_passes(self):
        place = self.controller.get_all_places()[0]
        self.controller.add_item("Espada", "Una espada de hierro", initial_location=place.name)
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_item_with_nonexistent_place_fails(self):
        self.controller.add_item("Espada", "Una espada de hierro", initial_location="abismo")
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("no existe en el mundo", err)

    # 5. Validación de conectividad de lugares (Places)
    def test_single_place_without_connections_passes(self):
        self.assertEqual(len(self.controller.get_all_places()), 1)
        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_multiple_places_without_connections_fails(self):
        loc = self.controller.world.locations[0]
        self.controller.add_place(loc.id, "Lugar Secundario", "Un sitio remoto.")
        self.assertEqual(len(self.controller.get_all_places()), 2)
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("no tienen conexiones", err)

    def test_place_connection_to_nonexistent_place_fails(self):
        p1 = self.controller.get_all_places()[0]
        p1.connections["North"] = Connection(target="Inexistente", distance=100, terrain_type="road")
        loc = self.controller.world.locations[0]
        p2 = self.controller.add_place(loc.id, "Lugar Secundario", "Un sitio remoto.")
        p2.connections["South"] = Connection(target=p1.name, distance=100, terrain_type="road")
        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("apunta a un lugar que no existe", err)

    def test_places_isolated_island_fails(self):
        loc = self.controller.world.locations[0]
        # p_inicio ya existe (p1)
        p2 = self.controller.add_place(loc.id, "Plaza Norte", "Norte")
        p3 = self.controller.add_place(loc.id, "Isla A", "Isla A")
        p4 = self.controller.add_place(loc.id, "Isla B", "Isla B")

        # Conectar p1 <-> p2
        self.controller.add_connection(self.controller.get_all_places()[0].name, "Plaza Norte", "North", "South", 100, "road")
        # Conectar p3 <-> p4 de forma aislada
        self.controller.add_connection("Isla A", "Isla B", "East", "West", 100, "road")

        valid, err = self.controller.validate_story()
        self.assertFalse(valid)
        self.assertIn("aislados", err)

    def test_fully_connected_places_passes(self):
        loc = self.controller.world.locations[0]
        p1_name = self.controller.get_all_places()[0].name
        p2 = self.controller.add_place(loc.id, "Plaza Norte", "Norte")
        p3 = self.controller.add_place(loc.id, "Castillo", "Castillo")

        self.controller.add_connection(p1_name, "Plaza Norte", "North", "South", 100, "road")
        self.controller.add_connection("Plaza Norte", "Castillo", "North", "South", 100, "road")

        valid, err = self.controller.validate_story()
        self.assertTrue(valid)
        self.assertIsNone(err)

    # 6. Guardado y sincronización
    def test_save_invalid_story_raises_value_error(self):
        self.controller.player = None
        with self.assertRaises(ValueError):
            self.controller.save_story("should_fail.aad")

    def test_save_valid_story_syncs_and_creates_aad(self):
        place = self.controller.get_all_places()[0]
        self.controller.add_npc("Guardián", "El guardián", initial_location=place.id)
        self.controller.add_item("Poción", "Cura heridas", initial_location=place.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_aad = os.path.join(temp_dir, "ValidStory.aad")
            self.controller.save_story(temp_aad)
            self.assertTrue(os.path.exists(temp_aad))

            # Verificar carga en nuevo controlador
            loaded = EditorController()
            loaded.load_story(temp_aad)
            self.assertEqual(loaded.player.initial_location, place.id)
            self.assertEqual(loaded.npcs[0].initial_location, place.id)
            self.assertEqual(loaded.items[0].initial_location, place.name)


if __name__ == "__main__":
    unittest.main()
