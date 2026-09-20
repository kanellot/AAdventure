"""Pruebas unitarias para la ejecución asíncrona y reactiva de AdventureSession."""

import json
import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from domains.projections import TurnResultProjection, UIStateProjection
from engines import AdventureSession
from engines.embedding.mock_backend import MockEmbeddingBackend
from engines.events import ThinkingEvent
from engines.listeners import SyncCollectingEventListener
from engines.transformer.mock_adapter import MockLLMAdapter


EventCollectorListener = SyncCollectingEventListener


class TestAsyncAdventureSession(unittest.TestCase):
    """Verifica el comportamiento reactivo, no bloqueante y la notificación de eventos."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.mock_llm = MockLLMAdapter({"msg": "Respuesta reactiva de prueba."})
        self.mock_emb = MockEmbeddingBackend()
        self.session = AdventureSession.start_for_testing(
            self.aad_path,
            llm_adapter=self.mock_llm,
            embedding_backend=self.mock_emb,
        )
        self.listener = EventCollectorListener()
        self.session.add_listener(self.listener)

    def tearDown(self):
        self.session.close()

    def test_add_and_remove_listener(self):
        extra_listener = EventCollectorListener()
        self.session.add_listener(extra_listener)
        self.assertIn(extra_listener, self.session._listeners)

        self.session.remove_listener(extra_listener)
        self.assertNotIn(extra_listener, self.session._listeners)

    def test_post_action_move_reactive_flow(self):
        # 1. Encolar acción de forma asíncrona
        task_id = self.session.post_action("MOVE", "Calle Pobre")
        self.assertTrue(task_id.startswith("task_"))

        # Inmediatamente tras post_action debe haberse emitido ThinkingEvent(is_thinking=True)
        self.assertGreater(len(self.listener.thinking_events), 0)
        first_json = self.listener.thinking_events[0]
        self.assertIsInstance(first_json, str)
        first_event = ThinkingEvent.model_validate_json(first_json)
        self.assertEqual(first_event.task_id, task_id)
        self.assertTrue(first_event.is_thinking)
        self.assertEqual(first_event.action, "MOVE")
        self.assertEqual(first_event.target, "Calle Pobre")

        # Verificar JSON parseable
        parsed_first = json.loads(first_json)
        self.assertTrue(parsed_first["is_thinking"])

        # 2. Esperar a que el worker procese el turno en segundo plano
        finished = self.listener.wait_for_completion(timeout=3.0)
        self.assertTrue(finished, "El worker thread no finalizó la tarea dentro del timeout.")

        # 3. Comprobar que se completó la tarea
        self.assertEqual(len(self.listener.completed_tasks), 1)
        completed_id, result_json = self.listener.completed_tasks[0]
        self.assertEqual(completed_id, task_id)
        self.assertIsInstance(result_json, str)
        result = TurnResultProjection.model_validate_json(result_json)
        self.assertEqual(result.author, "Dungeon Master")

        # 4. Comprobar actualización de estado
        self.assertGreater(len(self.listener.state_updates), 0)
        state_json = self.listener.state_updates[-1]
        self.assertIsInstance(state_json, str)
        state = UIStateProjection.model_validate_json(state_json)
        self.assertEqual(state.current_location, "Calle Pobre")

        # 5. Comprobar que ThinkingEvent finalizó con is_thinking=False
        last_json = self.listener.thinking_events[-1]
        last_event = ThinkingEvent.model_validate_json(last_json)
        self.assertEqual(last_event.task_id, task_id)
        self.assertFalse(last_event.is_thinking)

    def test_post_message_in_talk_mode(self):
        # Iniciar diálogo con el tabernero
        self.session.execute_action("TALK", "npc_tabernero")
        self.listener.reset_events()

        # Enviar mensaje reactivo
        task_id = self.session.post_message("Hola tabernero!")
        self.assertTrue(task_id.startswith("task_"))

        finished = self.listener.wait_for_completion(timeout=3.0)
        self.assertTrue(finished)

        self.assertEqual(len(self.listener.completed_tasks), 1)
        completed_id, result_json = self.listener.completed_tasks[0]
        self.assertEqual(completed_id, task_id)
        result = TurnResultProjection.model_validate_json(result_json)
        self.assertNotEqual(result.author, "SYSTEM")

    def test_synchronous_execute_action_notifies_listeners(self):
        # execute_action sigue funcionando de modo síncrono y notifica a los listeners
        result = self.session.execute_action("MOVE", "Plaza Mayor")
        self.assertIsInstance(result, TurnResultProjection)
        self.assertEqual(result.author, "Dungeon Master")

        # Debe haber emitido Thinking=True, completado, estado y Thinking=False
        self.assertGreater(len(self.listener.completed_tasks), 0)
        self.assertGreater(len(self.listener.thinking_events), 1)
        # El último thinking event debe ser False
        last_event = ThinkingEvent.model_validate_json(self.listener.thinking_events[-1])
        self.assertFalse(last_event.is_thinking)

    def test_autonomous_actions_decoupled_queueing(self):
        # Inyectar una acción autónoma simulada en el motor durante la ejecución de una tarea
        original_execute_action = self.session._execute_action_core

        def mock_core_with_autonomous(action, target, player_input=""):
            # Simular que el motor detectó un LoreBlock de diálogo autónomo solo en la primera acción
            if action == "MOVE":
                self.session._engine.pending_autonomous_actions.append({
                    "action": "TALK",
                    "target": "npc_tabernero",
                    "prompt": "Bienvenido viajero.",
                })
            return original_execute_action(action, target, player_input=player_input)

        with patch.object(self.session, "_execute_action_core", side_effect=mock_core_with_autonomous):
            task_id = self.session.post_action("MOVE", "Calle Pobre")

            # Esperar a que se procesen la tarea principal y la secundaria autónoma
            # La tarea principal + la tarea autónoma = 2 tareas completadas
            max_wait = 4.0
            start = time.time()
            while len(self.listener.completed_tasks) < 2 and (time.time() - start) < max_wait:
                time.sleep(0.05)

            self.assertEqual(len(self.listener.completed_tasks), 2)
            first_task_id = self.listener.completed_tasks[0][0]
            second_task_id = self.listener.completed_tasks[1][0]

            self.assertEqual(first_task_id, task_id)
            self.assertTrue(second_task_id.startswith("lore_"))

    def test_wait_idle(self):
        self.session.post_action("MOVE", "Calle Pobre")
        idle = self.session.wait_idle(timeout=4.0)
        self.assertTrue(idle)
        self.assertEqual(len(self.listener.completed_tasks), 1)

    def test_worker_error_handling(self):
        # Forzar un error en _execute_action_core
        with patch.object(self.session, "_execute_action_core", side_effect=RuntimeError("Fallo simulado")):
            task_id = self.session.post_action("MOVE", "Calle Pobre")

            # Esperar a que se apague el thinking por error
            finished = self.listener.thinking_done_event.wait(timeout=3.0)
            self.assertTrue(finished)

            # Verificar que se notificó el error
            self.assertEqual(len(self.listener.errors), 1)
            err_task_id, err_msg, err_code = self.listener.errors[0]
            self.assertEqual(err_task_id, task_id)
            self.assertIn("Fallo simulado", err_msg)
            self.assertEqual(err_code, "RuntimeError")

            # Verificar que el thinking finalizó con False y mensaje de error
            last_event = ThinkingEvent.model_validate_json(self.listener.thinking_events[-1])
            self.assertFalse(last_event.is_thinking)
            self.assertIn("Error:", last_event.message)


if __name__ == "__main__":
    unittest.main()
