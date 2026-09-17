"""Pruebas unitarias para GameEngine y ciclo de simulación."""

import unittest
import os
from domains import UIStateProjection, AvailableActionsProjection, LoreGraphProjection, TurnResultProjection
from engines.game.engine import GameEngine
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.engine import TransformerEngine


class DummyNarratorAdapter(BaseLLMAdapter):
    def generate(self, prompt: str, profile_name: str = "narrator", response_schema=None, schema_name=None):
        return {"msg": "Avanzas con determinación por el camino.", "confidence": 1.0}


class TestGameEngine(unittest.TestCase):
    """Verifica la inicialización, proyecciones y ciclo de turno de GameEngine."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)

    def tearDown(self):
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_engine_initialization_from_aad(self):
        self.assertIsNotNone(self.engine.temp_dir)
        self.assertTrue(os.path.isdir(self.engine.temp_dir))
        self.assertIsNotNone(self.engine.game_state_controller)
        self.assertEqual(self.engine.game_state_controller.place.id, "p_00")

    def test_ui_state_projection(self):
        ui = self.engine.get_ui_state_projection()
        self.assertIsInstance(ui, UIStateProjection)
        self.assertEqual(ui.player_name, "Aventurero")
        self.assertEqual(ui.current_location, "Plaza Mayor")
        self.assertEqual(ui.game_state, "EXPLORE")

    def test_available_actions_projection(self):
        actions = self.engine.get_available_actions_projection()
        self.assertIsInstance(actions, AvailableActionsProjection)
        self.assertGreater(len(actions.moves), 0)
        # Hay al menos una salida desde Plaza Mayor
        targets = [m.target for m in actions.moves]
        self.assertIn("Calle Pobre", targets)

    def test_lore_graph_projection(self):
        lg = self.engine.get_lore_graph_projection()
        self.assertIsInstance(lg, LoreGraphProjection)
        self.assertGreater(lg.total_count, 0)
        self.assertEqual(len(lg.blocks), lg.total_count)

    def test_execute_turn_with_mock_transformer(self):
        mock_dm = TransformerEngine(DummyNarratorAdapter())
        res = self.engine.execute_turn(
            action="MOVE",
            target="Calle Pobre",
            player_input="ir hacia la calle pobre",
            dm=mock_dm,
        )
        self.assertIsInstance(res, TurnResultProjection)
        self.assertTrue(bool(res.msg))
        self.assertEqual(self.engine.game_state_controller.place.id, "p_01")


if __name__ == "__main__":
    unittest.main()
