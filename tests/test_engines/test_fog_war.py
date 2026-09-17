"""Pruebas unitarias para el sistema de Niebla de Guerra (FogWar)."""

import unittest
from domains.world import World, Location, Place, Connection
from domains.npcs import NPC
from engines.game.utils.fog_war import FogWar, PlaceItem


class TestFogWar(unittest.TestCase):
    """Verifica el cálculo de visibilidad, lugares visitados, ocultos y revelación de NPCs."""

    def setUp(self):
        p1 = Place(
            id="p_01",
            name="Plaza Mayor",
            description="Una concurrida plaza.",
            visible_entities=["npc_alcalde"],
            connections={"norte": Connection(target="Calle Pobre", distance=100, terrain_type="village")},
        )
        p2 = Place(
            id="p_02",
            name="Calle Pobre",
            description="Una calle estrecha.",
            visible_entities=["npc_mendigo"],
            connections={
                "sur": Connection(target="Plaza Mayor", distance=100, terrain_type="village"),
                "norte": Connection(target="Taberna", distance=100, terrain_type="village"),
            },
        )
        p3 = Place(
            id="p_03",
            name="Taberna",
            description="Una taberna ruidosa.",
            connections={"sur": Connection(target="Calle Pobre", distance=100, terrain_type="village")},
        )

        loc = Location(id="l_01", name="Villa", description="Una villa modesta.", places=[p1, p2, p3])
        self.world = World(id="w_01", name="Mundo Test", description="Un mundo de prueba.", locations=[loc])

        self.npc1 = NPC(id="npc_alcalde", name="Alcalde", description="El alcalde de la villa.", initial_place="p_01")
        self.npc2 = NPC(id="npc_mendigo", name="Mendigo", description="Un mendigo harapiento.", initial_place="p_02")
        self.npcs = {"npc_alcalde": self.npc1, "npc_mendigo": self.npc2}

        self.fog = FogWar(
            world=self.world,
            npcs=self.npcs,
            initial_place="Plaza Mayor",
        )

    def test_initial_visibility_state(self):
        self.assertTrue(self.fog.is_visited("Plaza Mayor"))
        self.assertFalse(self.fog.is_visited("Calle Pobre"))
        self.assertTrue(self.fog.is_visible("Calle Pobre"))
        self.assertTrue(self.fog.is_hidden("Taberna"))

        visited = self.fog.get_visited_places()
        self.assertEqual(visited, ["Plaza Mayor"])

        visible = self.fog.get_visible_places()
        self.assertIn("Calle Pobre", visible)
        self.assertNotIn("Taberna", visible)

    def test_initial_npc_visibility(self):
        # NPC en el lugar visitado está visible, en lugar adyacente aún no visitado permanece oculto
        visible_npcs = self.fog.get_visible_npcs()
        self.assertIn("Alcalde", visible_npcs)
        self.assertNotIn("Mendigo", visible_npcs)

    def test_visit_reveals_connected_places_and_npcs(self):
        visited_new = self.fog.visit("Calle Pobre")
        self.assertTrue(visited_new)
        self.assertTrue(self.fog.is_visited("Calle Pobre"))

        # Taberna pasa a ser visible
        self.assertTrue(self.fog.is_visible("Taberna"))
        self.assertFalse(self.fog.is_hidden("Taberna"))

        # El mendigo ahora es visible
        visible_npcs = self.fog.get_visible_npcs()
        self.assertIn("Mendigo", visible_npcs)

    def test_place_item_compatibility(self):
        item = PlaceItem("Plaza Mayor", status="visited")
        self.assertEqual(str(item), "Plaza Mayor")
        self.assertEqual(item.status, "visited")
        self.assertEqual(item.get("status"), "visited")
        self.assertEqual(item.to_dict(), {"name": "Plaza Mayor", "status": "visited"})


if __name__ == "__main__":
    unittest.main()
