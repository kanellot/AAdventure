"""Pruebas unitarias para GameStateController y WorldState."""

import unittest
import os
import shutil
from adventure_packager import AdventurePackager
from domains.world import Place
from domains.player import Player
from engines.game.engine import GameEngine
from engines.game.state_controller import WorldState, GameStateController


class TestStateController(unittest.TestCase):
    """Verifica el estado del mundo, navegación de entidades y propiedades del controlador."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)
        self.ctrl = self.engine.game_state_controller

    def tearDown(self):
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_world_state_loaded_entities(self):
        ws = self.ctrl.world_state
        self.assertIsNotNone(ws.world)
        self.assertGreater(len(ws.places_by_id), 0)
        self.assertGreater(len(ws.npcs), 0)
        self.assertIsNotNone(ws.player)
        self.assertGreater(len(ws.lore_blocks), 0)

    def test_controller_active_properties(self):
        self.assertIsInstance(self.ctrl.place, Place)
        self.assertEqual(self.ctrl.place.id, "p_00")

        self.assertIsInstance(self.ctrl.player, Player)
        self.assertEqual(self.ctrl.player.id, "player")

        self.assertIn("npc_tabernero", self.ctrl.world_state.npcs)
        self.assertIsInstance(self.ctrl.npcs, dict)

    def test_location_and_place_helpers(self):
        locs = self.ctrl.get_location_list()
        self.assertGreater(len(locs), 0)
        self.assertTrue(any(l["name"] == "Villa Roca" for l in locs))

        curr_loc = self.ctrl.get_current_location()
        self.assertIsNotNone(curr_loc)
        self.assertEqual(curr_loc["name"], "Villa Roca")

        places = self.ctrl.get_places_list()
        self.assertTrue(any(p["id"] == "p_00" for p in places))
        self.assertTrue(any(p["id"] == "p_03" for p in places))

        npcs = self.ctrl.get_npc_list()
        self.assertTrue(any(n["id"] == "npc_tabernero" for n in npcs))

    def test_time_advancement(self):
        initial_time = self.ctrl.elapsed_time
        self.ctrl.add_time(15)
        self.assertEqual(self.ctrl.elapsed_time, initial_time + 15)


if __name__ == "__main__":
    unittest.main()
