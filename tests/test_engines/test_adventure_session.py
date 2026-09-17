"""Pruebas unitarias para la fachada pública AdventureSession y caja cerrada de engines."""

import os
import unittest
from domains import (
    AvailableActionsProjection,
    GameStateProjection,
    LoreGraphProjection,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
)
from engines import AdventureSession
from engines.embedding.mock_backend import MockEmbeddingBackend
from engines.transformer.mock_adapter import MockLLMAdapter


class TestAdventureSession(unittest.TestCase):
    """Verifica el contrato público, comportamiento defensivo y transiciones de AdventureSession."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.mock_llm = MockLLMAdapter({"msg": "Respuesta narrativa de prueba."})
        self.mock_emb = MockEmbeddingBackend()
        self.session = AdventureSession.start_for_testing(
            self.aad_path,
            llm_adapter=self.mock_llm,
            embedding_backend=self.mock_emb,
        )

    def tearDown(self):
        self.session.close()

    def test_session_initialization_and_metadata(self):
        self.assertFalse(self.session.is_closed)
        self.assertEqual(self.session.get_player_name(), "Aventurero")
        self.assertEqual(self.session.get_world_name(), "Shire")
        targets = self.session.get_all_target_names()
        self.assertGreater(len(targets), 0)
        self.assertIn("Plaza Mayor", targets)

    def test_projections(self):
        ui = self.session.get_ui_state()
        self.assertIsInstance(ui, UIStateProjection)
        self.assertEqual(ui.game_state, "EXPLORE")
        self.assertFalse(ui.can_send_message)
        self.assertIn("MOVE", ui.allowed_actions)
        self.assertIn("TALK", ui.allowed_actions)
        self.assertIn("LOOK", ui.allowed_actions)

        actions = self.session.get_available_actions()
        self.assertIsInstance(actions, AvailableActionsProjection)
        self.assertGreater(len(actions.moves), 0)

        gs = self.session.get_game_state()
        self.assertIsInstance(gs, GameStateProjection)
        self.assertEqual(gs.player_state, "EXPLORE")

        nav = self.session.get_navigation_tree()
        self.assertIsInstance(nav, WorldHierarchyProjection)

        entities = self.session.get_entities_tree()
        self.assertIsInstance(entities, WorldHierarchyProjection)

        lg = self.session.get_lore_graph()
        self.assertIsInstance(lg, LoreGraphProjection)

    def test_execute_action_move_success(self):
        res = self.session.execute_action("MOVE", "Calle Pobre")
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "Dungeon Master")
        ui = self.session.get_ui_state()
        self.assertEqual(ui.current_location, "Calle Pobre")
        self.assertEqual(ui.game_state, "EXPLORE")

    def test_execute_action_defensive_invalid_command(self):
        # Acción desconocida
        res = self.session.execute_action("DANCE", "Plaza Mayor")
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "SYSTEM")
        self.assertIn("no reconocida", res.msg)

        # Target vacío
        res2 = self.session.execute_action("MOVE", "")
        self.assertIsInstance(res2, TurnResultProjection)
        self.assertEqual(res2.author, "SYSTEM")
        self.assertIn("especificar un objetivo", res2.msg)

    def test_send_message_in_explore_returns_discrepancy(self):
        # En modo EXPLORE, send_message no debe lanzar excepción sino informar de la discrepancia
        res = self.session.send_message("Hola, ¿hay alguien aquí?")
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "SYSTEM")
        self.assertIn("EXPLORE", res.msg)
        self.assertIn("Discrepancia de estado", res.info_msg)

    def test_send_message_in_talk_mode(self):
        # Iniciar diálogo con un NPC visible o del mundo
        npc_targets = self.session.get_available_actions().npcs
        target_npc = npc_targets[0] if npc_targets else "npc_tabernero"

        res_talk = self.session.execute_action("TALK", target_npc)
        self.assertIsInstance(res_talk, TurnResultProjection)

        ui = self.session.get_ui_state()
        self.assertEqual(ui.game_state, "TALK")
        self.assertTrue(ui.can_send_message)

        # Ahora send_message debe ejecutarse normalmente
        res_msg = self.session.send_message("¿Qué novedades hay en el pueblo?")
        self.assertIsInstance(res_msg, TurnResultProjection)
        self.assertNotEqual(res_msg.author, "SYSTEM")

    def test_abrupt_move_from_talk_state(self):
        # 1. Poner al jugador en estado TALK
        npc_targets = self.session.get_available_actions().npcs
        target_npc = npc_targets[0] if npc_targets else "npc_tabernero"
        self.session.execute_action("TALK", target_npc)

        ui_before = self.session.get_ui_state()
        self.assertEqual(ui_before.game_state, "TALK")

        # 2. El usuario ejecuta MOVE mientras conversa -> interrupción abrupta
        res_move = self.session.execute_action("MOVE", "Calle Pobre")
        self.assertIsInstance(res_move, TurnResultProjection)
        self.assertEqual(res_move.author, "Dungeon Master")
        self.assertIn("Has interrumpido la conversación abruptamente", res_move.info_msg or "")

        # 3. Verificar que el estado volvió a EXPLORE y la conversación se limpió
        ui_after = self.session.get_ui_state()
        self.assertEqual(ui_after.game_state, "EXPLORE")
        self.assertIsNone(ui_after.player_target)
        self.assertIsNone(ui_after.active_npc_affinity)
        self.assertEqual(ui_after.current_location, "Calle Pobre")

    def test_context_manager_and_closed_session(self):
        with AdventureSession.start_for_testing(self.aad_path) as s:
            self.assertFalse(s.is_closed)
            ui = s.get_ui_state()
            self.assertEqual(ui.player_name, "Aventurero")

        self.assertTrue(s.is_closed)
        res = s.execute_action("MOVE", "Plaza Mayor")
        self.assertEqual(res.author, "SYSTEM")
        self.assertIn("cerrada", res.msg)


if __name__ == "__main__":
    unittest.main()
