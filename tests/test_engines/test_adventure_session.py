"""Pruebas unitarias para la fachada pública AdventureSession."""

import json
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
from engines.listeners import SyncCollectingEventListener


class TestAdventureSession(unittest.TestCase):
    """Verifica el contrato público reactivo, interfaz única post_action y acceso al motor."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.session = AdventureSession.create(self.aad_path)
        self.listener = SyncCollectingEventListener()
        self.session.add_listener(self.listener)

    def tearDown(self):
        self.session.close()

    def _get_latest_ui_state(self) -> UIStateProjection:
        self.assertGreater(len(self.listener.state_updates), 0, "No se registraron actualizaciones de estado.")
        return UIStateProjection.model_validate_json(self.listener.state_updates[-1])

    def _get_latest_turn_result(self) -> TurnResultProjection:
        self.assertGreater(len(self.listener.completed_tasks), 0, "No se completó ninguna tarea.")
        return TurnResultProjection.model_validate_json(self.listener.completed_tasks[-1][1])

    def test_single_entry_interface(self):
        """Verifica que AdventureSession expone únicamente post_action como método de entrada de datos."""
        # 1. Métodos y atributos públicos permitidos en AdventureSession
        self.assertTrue(hasattr(AdventureSession, "create"))
        self.assertTrue(hasattr(self.session, "start"))
        self.assertTrue(hasattr(self.session, "save"))
        self.assertTrue(hasattr(self.session, "close"))
        self.assertTrue(hasattr(self.session, "add_listener"))
        self.assertTrue(hasattr(self.session, "remove_listener"))
        self.assertTrue(hasattr(self.session, "post_action"))
        self.assertTrue(hasattr(self.session, "wait_idle"))
        self.assertTrue(hasattr(self.session, "is_closed"))
        self.assertTrue(hasattr(self.session, "aad_path"))

        # 2. Propiedades y métodos prohibidos en AdventureSession (Cero fugas de debug o motor interno)
        forbidden_members = [
            "engine",
            "_listeners",
            "post_message",
            "send_message",
            "execute_action",
            "start_for_testing",
            "get_ui_state",
            "get_game_state",
            "get_navigation_tree",
            "get_entities_tree",
            "get_lore_graph",
            "get_available_actions",
            "get_all_target_names",
            "get_player_name",
            "get_world_name",
        ]
        for member_name in forbidden_members:
            self.assertFalse(
                hasattr(self.session, member_name),
                f"AdventureSession NO debe exponer '{member_name}'.",
            )

        # 3. Comprobar que DebugAdventureSession no existe en engines
        import engines
        self.assertFalse(
            hasattr(engines, "DebugAdventureSession"),
            "DebugAdventureSession debe estar completamente eliminado.",
        )

    def test_engine_introspection_direct_access(self):
        """Verifica que GameEngine provee todas las proyecciones para herramientas de diagnóstico."""
        from engines.game.engine import GameEngine
        engine = GameEngine(aad_path=self.aad_path)
        self.assertIsNotNone(engine)

        self.assertEqual(engine.get_player_name(), "Aventurero")
        self.assertEqual(engine.get_world_name(), "Shire")

        targets = engine.get_all_target_names()
        self.assertGreater(len(targets), 0)
        self.assertIn("Plaza Mayor", targets)

        ui = engine.get_ui_state_projection()
        self.assertIsInstance(ui, UIStateProjection)
        self.assertEqual(ui.game_state, "EXPLORE")
        self.assertFalse(ui.can_send_message)
        self.assertIn("MOVE", ui.allowed_actions)

        actions = engine.get_available_actions_projection()
        self.assertIsInstance(actions, AvailableActionsProjection)
        self.assertGreater(len(actions.moves), 0)

        gs = engine.get_game_state_projection()
        self.assertIsInstance(gs, GameStateProjection)
        self.assertEqual(gs.player_state, "EXPLORE")

        nav = engine.get_navigation_hierarchy()
        self.assertIsInstance(nav, WorldHierarchyProjection)

        entities = engine.get_entities_hierarchy()
        self.assertIsInstance(entities, WorldHierarchyProjection)

        lg = engine.get_lore_graph_projection()
        self.assertIsInstance(lg, LoreGraphProjection)

    def test_state_on_connect(self):
        """Verifica que add_listener emite inmediatamente on_state_updated con JSON válido (State-on-Connect)."""
        new_listener = SyncCollectingEventListener()
        self.assertEqual(len(new_listener.state_updates), 0)

        self.session.add_listener(new_listener)

        self.assertEqual(len(new_listener.state_updates), 1)
        state_json = new_listener.state_updates[0]
        self.assertIsInstance(state_json, str)

        parsed = json.loads(state_json)
        self.assertIn("player_name", parsed)
        self.assertIn("current_location", parsed)

        state_dto = UIStateProjection.model_validate_json(state_json)
        self.assertEqual(state_dto.player_name, "Aventurero")
        self.assertEqual(state_dto.game_state, "EXPLORE")

        self.session.remove_listener(new_listener)

    def test_post_action_move_success(self):
        task_id = self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()

        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "Dungeon Master")

        ui = self._get_latest_ui_state()
        self.assertEqual(ui.current_location, "Calle Pobre")
        self.assertEqual(ui.game_state, "EXPLORE")

    def test_post_action_defensive_invalid_command(self):
        # Acción desconocida
        self.session.post_action("DANCE", "Plaza Mayor")
        self.session.wait_idle()
        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertIn("no reconocida", res.output.msg)

        # Target vacío en MOVE
        self.session.post_action("MOVE", "")
        self.session.wait_idle()
        res2 = self._get_latest_turn_result()
        self.assertEqual(res2.output.author, "SYSTEM")
        self.assertIn("indicar un destino", res2.output.msg)

    def test_post_action_message_in_explore_returns_discrepancy(self):
        # En modo EXPLORE, texto libre vía post_action informa de la discrepancia
        self.session.post_action(action="", target="", player_input="Hola, ¿hay alguien aquí?")
        self.session.wait_idle()
        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertIn("Debes seleccionar una acción", res.output.msg)

    def test_post_action_message_in_talk_mode(self):
        # Mover a Calle Pobre donde se encuentra el mendigo
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()

        self.session.post_action("TALK", "npc_mendigo")
        self.session.wait_idle()

        ui = self._get_latest_ui_state()
        self.assertEqual(ui.game_state, "TALK")
        self.assertTrue(ui.can_send_message)

        # Ahora el diálogo se envía con post_action
        self.session.post_action(action="", target="", player_input="¿Qué novedades hay en el pueblo?")
        self.session.wait_idle()
        res_msg = self._get_latest_turn_result()
        self.assertNotEqual(res_msg.output.author, "SYSTEM")

    def test_abrupt_move_from_talk_state(self):
        # 1. Mover a Calle Pobre y poner al jugador en estado TALK con el mendigo
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("TALK", "npc_mendigo")
        self.session.wait_idle()

        ui_before = self._get_latest_ui_state()
        self.assertEqual(ui_before.game_state, "TALK")

        # 2. El usuario ejecuta MOVE mientras conversa -> desenganche universal
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()
        res_move = self._get_latest_turn_result()
        self.assertEqual(res_move.output.author, "Dungeon Master")

        # 3. Verificar que el estado volvió a EXPLORE y la conversación se desenganchó
        ui_after = self._get_latest_ui_state()
        self.assertEqual(ui_after.game_state, "EXPLORE")
        self.assertIsNone(ui_after.player_target)
        self.assertIsNone(ui_after.active_npc_affinity)
        self.assertEqual(ui_after.current_location, "Plaza Mayor")

    def test_context_manager_and_closed_session(self):
        with AdventureSession.create(self.aad_path) as s:
            self.assertFalse(s.is_closed)
            self.assertEqual(s.aad_path, self.aad_path)

        self.assertTrue(s.is_closed)

        closed_listener = SyncCollectingEventListener()
        s.add_listener(closed_listener)
        s.post_action("MOVE", "Plaza Mayor")
        s.wait_idle()

        self.assertGreater(len(closed_listener.completed_tasks), 0)
        res = TurnResultProjection.model_validate_json(closed_listener.completed_tasks[-1][1])
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertIn("cerrada", res.output.msg)

    def test_session_start_executes_turn_0(self):
        """Verifica que session.start() encola y ejecuta el Turno 0 con texto inicial y popups."""
        task_id = self.session.start()
        self.assertTrue(task_id.startswith("task_"))
        self.session.wait_idle()

        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "Dungeon Master")
        self.assertEqual(res.output.type, "msg")
        self.assertIn("Villa Roca", res.output.msg)
        self.assertIn("Tu gran aventura", res.output.msg)
        self.assertEqual(res.output.popup_title, "Llegada a Villa Roca")
        self.assertIn("Villa Roca", res.output.popup_message)


if __name__ == "__main__":
    unittest.main()
