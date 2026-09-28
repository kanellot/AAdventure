"""Pruebas de integración End-to-End para la nueva arquitectura del motor AAdventure."""

import json
import os
import shutil
import tempfile
import unittest

from domains import TurnResultProjection, UIStateProjection
from engines import AdventureSession
from engines.game.engine import GameEngine
from engines.listeners import SyncCollectingEventListener


class TestNewEngineE2E(unittest.TestCase):
    """Pruebas completas de integración de extremo a extremo (E2E) con Adventure.aad."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(aad_path=self.aad_path)
        self.session = AdventureSession(game_engine=self.engine, aad_path=self.aad_path)
        self.listener = SyncCollectingEventListener()
        self.session.add_listener(self.listener)

    def tearDown(self):
        self.session.close()

    def _get_latest_turn_result(self) -> TurnResultProjection:
        self.assertGreater(len(self.listener.completed_tasks), 0, "No se completó ninguna tarea.")
        return TurnResultProjection.model_validate_json(self.listener.completed_tasks[-1][1])

    def _get_latest_ui_state(self) -> UIStateProjection:
        self.assertGreater(len(self.listener.state_updates), 0, "No se registraron actualizaciones de estado.")
        return UIStateProjection.model_validate_json(self.listener.state_updates[-1])

    def test_e2e_session_lifecycle_and_metadata(self):
        """Verifica el arranque, metadatos y estado inicial sin niebla alterada."""
        self.assertFalse(self.session.is_closed)
        self.assertEqual(self.engine.get_player_name(), "Aventurero")
        self.assertEqual(self.engine.get_world_name(), "Shire")

        targets = self.engine.get_all_target_names()
        self.assertIn("Plaza Mayor", targets)
        self.assertIn("Calle Pobre", targets)

        # Estado inicial (State-on-Connect)
        ui = self.engine.get_ui_state_projection()
        self.assertEqual(ui.player_name, "Aventurero")
        self.assertEqual(ui.current_location, "Plaza Mayor")
        self.assertEqual(ui.game_state, "EXPLORE")
        self.assertFalse(ui.can_send_message)

    def test_e2e_free_text_strict_rejection_in_explore(self):
        """El texto libre en EXPLORE debe ser rechazado sin excepción y notificado en la proyección."""
        self.session.post_action(action="", target="", player_input="Hola, ¿hay alguien aquí?")
        self.session.wait_idle()

        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertEqual(res.output.player_state, "EXPLORE")
        self.assertIn("Debes seleccionar una acción", res.output.msg)

    def test_e2e_move_and_fog_of_war_update(self):
        """El desplazamiento actualiza posición, niebla de guerra y emite eventos reactivos."""
        task_id = self.session.post_action("MOVE", "Calle Pobre")
        self.assertTrue(task_id.startswith("task_"))
        self.session.wait_idle()

        res = self._get_latest_turn_result()
        self.assertEqual(res.output.author, "Dungeon Master")

        ui = self._get_latest_ui_state()
        self.assertEqual(ui.current_location, "Calle Pobre")
        self.assertEqual(ui.game_state, "EXPLORE")

        # Comprobar Niebla de Guerra: Calle Pobre es visited
        places_by_id = {p.id: p for loc in res.map.locations for p in loc.places}
        self.assertEqual(places_by_id["p_01"].status, "visited")

    def test_e2e_dialogue_flow_and_universal_disengagement(self):
        """Flujo completo de conversación con NPC y desenganche universal al desplazarse."""
        # 1. Iniciar diálogo con el mendigo en Calle Pobre
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()

        self.session.post_action("TALK", "npc_mendigo")
        self.session.wait_idle()

        res_talk = self._get_latest_turn_result()
        self.assertEqual(res_talk.output.player_state, "TALK")
        self.assertEqual(res_talk.output.author, "Mendigo")

        ui_talk = self._get_latest_ui_state()
        self.assertEqual(ui_talk.game_state, "TALK")
        self.assertEqual(ui_talk.player_target, "npc_mendigo")
        self.assertTrue(ui_talk.can_send_message)

        # 2. Enviar mensaje de diálogo libre en modo TALK
        self.session.post_action(action="", target="", player_input="¿Tienes alguna información útil?")
        self.session.wait_idle()

        res_msg = self._get_latest_turn_result()
        self.assertEqual(res_msg.output.author, "Mendigo")
        self.assertEqual(res_msg.output.player_state, "TALK")

        # 3. Desenganche Universal: Ejecutar LOOK cambia de TALK a LOOK
        self.session.post_action("LOOK", "")
        self.session.wait_idle()

        res_look = self._get_latest_turn_result()
        self.assertEqual(res_look.output.author, "Dungeon Master")
        self.assertEqual(res_look.output.player_state, "LOOK")

        ui_look = self._get_latest_ui_state()
        self.assertEqual(ui_look.game_state, "LOOK")
        self.assertEqual(ui_look.player_target, "p_01")

        # 4. Desenganche Universal: Moverse vuelve a EXPLORE y limpia player_target
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()

        ui_explore = self._get_latest_ui_state()
        self.assertEqual(ui_explore.game_state, "EXPLORE")
        self.assertIsNone(ui_explore.player_target)
        self.assertEqual(ui_explore.current_location, "Plaza Mayor")

    def test_e2e_persistence_save_and_load(self):
        """Verifica la persistencia determinista guardando y recargando el estado."""
        # Modificar estado: desplazarse y ganar oro
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        ctrl = self.engine.game_state_controller
        initial_gold = ctrl.game_state.gold
        ctrl.add_gold(15)

        # Guardar en slot de prueba
        ctrl.save("slot_test_e2e")

        # Crear nuevo controlador y cargar partida
        new_ctrl = GameEngine(aad_path=self.aad_path).game_state_controller
        new_ctrl.load("slot_test_e2e")

        self.assertEqual(new_ctrl.game_state.current_location, "p_01")
        self.assertEqual(new_ctrl.game_state.gold, initial_gold + 15)

        # Limpiar archivo de guardado
        save_file = os.path.join(ctrl.saves_directory, "slot_test_e2e.json")
        if os.path.exists(save_file):
            os.remove(save_file)

    def test_e2e_context_manager_and_closed_session(self):
        """Verifica el uso con context manager ('with') y el manejo seguro tras close()."""
        with AdventureSession.create(self.aad_path) as s:
            self.assertFalse(s.is_closed)
            self.assertEqual(s.aad_path, self.aad_path)

        self.assertTrue(s.is_closed)

        # Llamar a post_action en sesión cerrada notifica inmediatamente sin bloquear en wait_idle
        closed_listener = SyncCollectingEventListener()
        s.add_listener(closed_listener)
        s.post_action("MOVE", "Plaza Mayor")
        s.wait_idle()

        self.assertGreater(len(closed_listener.completed_tasks), 0)
        res = TurnResultProjection.model_validate_json(closed_listener.completed_tasks[-1][1])
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertIn("cerrada", res.output.msg)


if __name__ == "__main__":
    unittest.main()
