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
        self.assertTrue(conn.passable)

        # Conexión bloqueada
        blocked = Connection(target="Cueva", distance=500, terrain_type="mountain", passable=False)
        self.assertFalse(blocked.passable)
        self.assertEqual(blocked.terrain_type, "mountain")

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

        world = World(id="w_01", name="Mundo de Fantasía", description="El reino", locations=[loc])
        self.assertEqual(world.name, "Mundo de Fantasía")
        self.assertEqual(len(world.locations), 1)
        self.assertEqual(world.locations[0].id, "loc_01")


if __name__ == "__main__":
    unittest.main()
