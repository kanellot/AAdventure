"""Pruebas unitarias para el sistema de Niebla de Guerra canónico (GameStateController)."""

import unittest
from domains.player import Player
from domains.world import World, Location, Place, Connection
from domains.npcs import NPC
from engines.game.state_controller import GameStateController


class TestFogWar(unittest.TestCase):
    """Verifica el cálculo de visibilidad, lugares visitados, ocultos y revelación bajo niebla de guerra."""

    def setUp(self):
        p1 = Place(
            id="p_01",
            name="Plaza Mayor",
            description="Una concurrida plaza.",
            connections={"norte": Connection(target="Calle Pobre", distance=100, terrain_type="village")},
        )
        p2 = Place(
            id="p_02",
            name="Calle Pobre",
            description="Una calle estrecha.",
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

        self.npc1 = NPC(id="npc_alcalde", name="Alcalde", description="El alcalde.", initial_location="p_01")
        self.npc2 = NPC(id="npc_mendigo", name="Mendigo", description="Un mendigo.", initial_location="p_02")
        self.npcs = [self.npc1, self.npc2]

        self.player = Player(id="player", name="Héroe", description="Protagonista", initial_location="p_01")
        self.controller = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=self.npcs,
            fog_war_enabled=True,
        )

    def _get_place_status(self, place_id: str) -> str:
        for loc in self.controller.game_state.entity_map:
            for p in loc.places:
                if p.id == place_id:
                    return p.status
        return "not_found"

    def test_initial_visibility_state(self):
        self.assertEqual(self._get_place_status("p_01"), "visited")
        self.assertEqual(self._get_place_status("p_02"), "visible")
        self.assertEqual(self._get_place_status("p_03"), "hidden")

    def test_visit_reveals_connected_places(self):
        self.controller.set_current_location("p_02")
        self.assertEqual(self._get_place_status("p_01"), "visited")
        self.assertEqual(self._get_place_status("p_02"), "visited")
        self.assertEqual(self._get_place_status("p_03"), "visible")

    def test_fog_war_disabled(self):
        ctrl = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=self.npcs,
            fog_war_enabled=False,
        )
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == "p_01":
                    self.assertEqual(p.status, "visited")
                else:
                    self.assertEqual(p.status, "visible")


if __name__ == "__main__":
    unittest.main()
