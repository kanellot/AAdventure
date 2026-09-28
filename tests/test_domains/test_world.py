"""Pruebas unitarias para los modelos de mundo y geografía (domains.world)."""

import unittest
from domains.world import Connection, Place, Location, World


class TestWorldModels(unittest.TestCase):
    """Pruebas de modelos de World, Location, Place y Connection."""

    def test_connection_defaults_and_validation(self):
        conn = Connection(target="Plaza Menor", distance=120, terrain_type="village")
        self.assertEqual(conn.target, "Plaza Menor")
        self.assertEqual(conn.distance, 120)
        self.assertEqual(conn.terrain_type, "village")

    def test_place_blocked_status(self):
        place_open = Place(id="p_01", name="Plaza", description="Plaza abierta")
        self.assertFalse(place_open.blocked_place)

        place_blocked = Place(id="p_02", name="Cueva Prohibida", description="Entrada sellada", blocked_place=True)
        self.assertTrue(place_blocked.blocked_place)

    def test_place_creation_and_connections(self):
        place = Place(
            id="p_01",
            name="Taberna",
            description="Una acogedora taberna de madera.",
            connections={
                "Norte": Connection(target="Plaza Mayor", distance=100, terrain_type="road")
            },
            visible_entities=["npc_tabernero", "obj_jarra"]
        )
        self.assertEqual(place.id, "p_01")
        self.assertEqual(place.name, "Taberna")
        self.assertIn("Norte", place.connections)
        self.assertEqual(place.connections["Norte"].distance, 100)
        self.assertIn("npc_tabernero", place.visible_entities)

    def test_location_and_world_hierarchy(self):
        p1 = Place(id="p_01", name="Plaza", description="Plaza")
        p2 = Place(id="p_02", name="Calle", description="Calle")
        loc = Location(id="loc_01", name="Villa Roca", description="Aldea pacífica", places=[p1, p2])
        self.assertEqual(len(loc.places), 2)
        self.assertEqual(loc.places[0].id, "p_01")

        world = World(
            id="w_01",
            name="Mundo de Fantasía",
            description="El reino",
            locations=[loc],
            initial_text="Bienvenido viajero, la niebla se disipa sobre el reino...",
        )
        self.assertEqual(world.name, "Mundo de Fantasía")
        self.assertEqual(len(world.locations), 1)
        self.assertEqual(world.locations[0].id, "loc_01")
        self.assertEqual(world.initial_text, "Bienvenido viajero, la niebla se disipa sobre el reino...")

    def test_world_initial_text_default_and_roundtrip(self):
        default_world = World(id="w_def", name="Mundo Base", description="Descripción base")
        self.assertEqual(default_world.initial_text, "")

        serialized = default_world.model_dump_json()
        deserialized = World.model_validate_json(serialized)
        self.assertEqual(deserialized.initial_text, "")

        custom_world = World(id="w_cust", name="Mundo Personalizado", description="Descripción cust", initial_text="Érase una vez...")
        deserialized_custom = World.model_validate_json(custom_world.model_dump_json())
        self.assertEqual(deserialized_custom.initial_text, "Érase una vez...")


if __name__ == "__main__":
    unittest.main()
