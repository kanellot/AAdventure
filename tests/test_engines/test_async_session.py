"""Pruebas unitarias para la ejecución asíncrona y reactiva de AdventureSession."""

import json
import os
import unittest
from unittest.mock import patch

from domains.projections import TurnResultProjection, UIStateProjection
from engines import AdventureSession
from engines.events import ThinkingEvent
from engines.listeners import SyncCollectingEventListener

EventCollectorListener = SyncCollectingEventListener


class TestAsyncAdventureSession(unittest.TestCase):
    """Verifica el comportamiento reactivo, no bloqueante y la notificación de eventos."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.session = AdventureSession.create(self.aad_path)
        self.listener = EventCollectorListener()
        self.session.add_listener(self.listener)

    def tearDown(self):
        self.session.close()

    def test_add_and_remove_listener(self):
        extra_listener = EventCollectorListener()
        self.session.add_listener(extra_listener)
        self.assertIn(extra_listener, self.session._engine.listeners)

        self.session.remove_listener(extra_listener)
        self.assertNotIn(extra_listener, self.session._engine.listeners)

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
        self.assertEqual(result.output.author, "Dungeon Master")

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
        # Mover a Calle Pobre y hablar con el mendigo
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("TALK", "npc_mendigo")
        self.session.wait_idle()
        self.listener.reset_events()

        # Enviar mensaje reactivo vía post_action unificado
        task_id = self.session.post_action(action="", target="", player_input="Hola mendigo!")
        self.assertTrue(task_id.startswith("task_"))

        finished = self.listener.wait_for_completion(timeout=3.0)
        self.assertTrue(finished)

        self.assertEqual(len(self.listener.completed_tasks), 1)
        completed_id, result_json = self.listener.completed_tasks[0]
        self.assertEqual(completed_id, task_id)
        result = TurnResultProjection.model_validate_json(result_json)
        self.assertNotEqual(result.output.author, "SYSTEM")

    def test_post_action_notifies_listeners(self):
        # post_action procesa la acción y notifica a los listeners de forma reactiva
        task_id = self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()

        # Debe haber emitido Thinking=True, completado, estado y Thinking=False
        self.assertGreater(len(self.listener.completed_tasks), 0)
        completed_id, result_json = self.listener.completed_tasks[-1]
        self.assertEqual(completed_id, task_id)
        result = TurnResultProjection.model_validate_json(result_json)
        self.assertEqual(result.output.author, "Dungeon Master")

        self.assertGreater(len(self.listener.thinking_events), 1)
        # El último thinking event debe ser False
        last_event = ThinkingEvent.model_validate_json(self.listener.thinking_events[-1])
        self.assertFalse(last_event.is_thinking)

    def test_autonomous_actions_decoupled_queueing(self):
        # En el nuevo GameEngine determinista, las acciones autónomas se ejecutan en cadena determinista
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.assertGreaterEqual(len(self.listener.completed_tasks), 1)

    def test_wait_idle(self):
        self.session.post_action("MOVE", "Calle Pobre")
        idle = self.session.wait_idle(timeout=4.0)
        self.assertTrue(idle)
        self.assertEqual(len(self.listener.completed_tasks), 1)

    def test_worker_error_handling(self):
        # Forzar un error en execute_turn
        with patch.object(self.session._engine, "execute_turn", side_effect=RuntimeError("Fallo simulado")):
            task_id = self.session.post_action("MOVE", "Calle Pobre")

            # Esperar a que se procese la tarea
            self.session.wait_idle()

            # Verificar que se notificó el error
            self.assertEqual(len(self.listener.errors), 1)
            err_task_id, err_msg, err_code = self.listener.errors[0]
            self.assertEqual(err_task_id, task_id)
            self.assertIn("Fallo simulado", err_msg)
            self.assertEqual(err_code, "ENGINE_ERROR")

            # Verificar que el thinking finalizó con False
            last_event = ThinkingEvent.model_validate_json(self.listener.thinking_events[-1])
            self.assertFalse(last_event.is_thinking)

    def test_push_action_sequential_delivery_and_thinking(self):
        """Verifica que una acción push se encola y entrega como segundo turno consecutivo e independiente."""
        ctrl = self.session._engine.game_state_controller
        push_block = {
            "id": "block_mendigo_push",
            "name": "Mendigo Intercept",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p_01",
                            "sub_condition": "current_location",
                        }
                    ]
                }
            ],
            "active_effects": [
                {
                    "action": "push",
                    "target": "npc_mendigo",
                    "directive": "¡Una moneda por favor!",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        ctrl.game_state.loreblocks.unknown.append(push_block)

        # Disparar MOVE
        self.session.post_action("MOVE", "Calle Pobre")
        finished = self.session.wait_idle(timeout=4.0)
        self.assertTrue(finished)

        # Deben haberse completado exactamente 2 tareas: 1 (MOVE de PLAYER) y 2 (TALK de LORE)
        self.assertEqual(len(self.listener.completed_tasks), 2)
        task1_id, res1_json = self.listener.completed_tasks[0]
        task2_id, res2_json = self.listener.completed_tasks[1]

        res1 = TurnResultProjection.model_validate_json(res1_json)
        res2 = TurnResultProjection.model_validate_json(res2_json)

        # Turno 1 es la narrativa de MOVE
        self.assertEqual(res1.output.author, "Dungeon Master")
        self.assertIn("Avanzas con precaución", res1.output.msg)

        # Turno 2 es la narrativa del push autónomo (Mendigo con bypass)
        self.assertIn("moneda", res2.output.msg)
        self.assertEqual(res2.output.author, "Mendigo")

        # Comprobar que hubo eventos Thinking tanto para PLAYER como para LORE
        lore_thinking = [
            ThinkingEvent.model_validate_json(e)
            for e in self.listener.thinking_events
            if ThinkingEvent.model_validate_json(e).source == "LORE"
        ]
        self.assertGreater(len(lore_thinking), 0)
        self.assertEqual(lore_thinking[0].action, "TALK")
        self.assertEqual(lore_thinking[0].target, "npc_mendigo")

    def test_push_action_depth_limit(self):
        """Verifica que un encadenamiento que alcanza MAX_AUTONOMOUS_CHAIN_DEPTH no encola más tareas."""
        ctrl = self.session._engine.game_state_controller
        loop_block = {
            "id": "block_loop_push",
            "name": "Loop Push",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p_01",
                            "sub_condition": "current_location",
                        }
                    ]
                }
            ],
            "active_effects": [
                {
                    "action": "push",
                    "target": "npc_mendigo",
                    "directive": "Bucle",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        ctrl.game_state.loreblocks.unknown.append(loop_block)

        max_depth = self.session._engine.MAX_AUTONOMOUS_CHAIN_DEPTH
        self.assertEqual(max_depth, 3)

        # Al ejecutar con depth >= MAX_AUTONOMOUS_CHAIN_DEPTH, no se encola nada en task_queue
        # Limpiar cola primero
        while not self.session._engine.worker.task_queue.empty():
            self.session._engine.worker.task_queue.get_nowait()

        self.session._engine.execute_turn(
            action="MOVE",
            target="Calle Pobre",
            autonomous_depth=max_depth,
        )
        self.assertEqual(self.session._engine.worker.task_queue.qsize(), 0)


if __name__ == "__main__":
    unittest.main()
