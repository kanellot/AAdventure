"""Pruebas unitarias para DTOs y eventos reactivos de comunicación Motor-UI."""

import json
import unittest
from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import (
    BaseEngineEventListener,
    EngineEventListener,
    EngineTask,
    ThinkingEvent,
)


class CustomTestListener(BaseEngineEventListener):
    """Listener concreto para verificar la recepción de eventos."""

    def __init__(self):
        self.thinking_events = []
        self.completed_tasks = []
        self.state_updates = []
        self.errors = []

    def on_thinking_changed(self, event_json: str) -> None:
        self.thinking_events.append(event_json)

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        self.completed_tasks.append((task_id, result_json))

    def on_state_updated(self, ui_state_json: str) -> None:
        self.state_updates.append(ui_state_json)

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        self.errors.append((task_id, error_message, error_code))


class TestEngineEvents(unittest.TestCase):
    """Verifica la serialización y contratos de eventos del motor."""

    def test_thinking_event_serialization(self):
        event = ThinkingEvent(
            task_id="task_12345",
            is_thinking=True,
            action="MOVE",
            target="Plaza Mayor",
            source="PLAYER",
            message="Pensando...",
        )
        self.assertEqual(event.task_id, "task_12345")
        self.assertTrue(event.is_thinking)
        self.assertEqual(event.action, "MOVE")
        self.assertEqual(event.target, "Plaza Mayor")
        self.assertEqual(event.source, "PLAYER")

        # Serialización JSON para Android JNI / clientes externos
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["task_id"], "task_12345")
        self.assertTrue(parsed["is_thinking"])
        self.assertEqual(parsed["action"], "MOVE")
        self.assertEqual(parsed["target"], "Plaza Mayor")

    def test_engine_task_defaults(self):
        task = EngineTask(task_id="t_001", action="TALK", target="npc_tabernero")
        self.assertEqual(task.task_id, "t_001")
        self.assertEqual(task.action, "TALK")
        self.assertEqual(task.target, "npc_tabernero")
        self.assertEqual(task.player_input, "")
        self.assertEqual(task.source, "PLAYER")
        self.assertGreater(task.created_at, 0)

        json_str = task.model_dump_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["source"], "PLAYER")

    def test_listener_protocol_conformance(self):
        listener = CustomTestListener()
        self.assertIsInstance(listener, EngineEventListener)

        # BaseEngineEventListener también cumple el protocolo
        base = BaseEngineEventListener()
        self.assertIsInstance(base, EngineEventListener)

        # Llamar métodos base vacíos no debe lanzar error
        base.on_thinking_changed("{}")
        base.on_task_completed("t", "{}")
        base.on_state_updated("{}")
        base.on_error("t", "error", "ERR_CODE")


if __name__ == "__main__":
    unittest.main()
