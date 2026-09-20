"""Pruebas unitarias para QtEngineListener del depurador."""

import unittest
from PySide6.QtWidgets import QApplication

from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import EngineEventListener, ThinkingEvent
from game_debugger.qt_listener import QtEngineListener


class TestQtEngineListener(unittest.TestCase):
    """Verifica la emisión de señales Qt y compatibilidad con el protocolo de eventos."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def setUp(self):
        self.listener = QtEngineListener()

    def test_protocol_conformance(self):
        self.assertIsInstance(self.listener, EngineEventListener)

    def test_thinking_changed_signal(self):
        emitted = []
        self.listener.thinking_changed.connect(lambda json_str: emitted.append(json_str))

        event = ThinkingEvent(
            task_id="t1",
            is_thinking=True,
            action="MOVE",
            target="Plaza",
            message="Pensando...",
        )
        self.listener.on_thinking_changed(event.model_dump_json())

        self.assertEqual(len(emitted), 1)
        j_str = emitted[0]
        self.assertIn('"is_thinking":true', j_str)
        self.assertIn("t1", j_str)

    def test_task_completed_signal(self):
        emitted = []
        self.listener.task_completed.connect(
            lambda t_id, j_str: emitted.append((t_id, j_str))
        )

        result = TurnResultProjection(author="Dungeon Master", msg="Te mueves con sigilo.")
        self.listener.on_task_completed("t2", result.model_dump_json())

        self.assertEqual(len(emitted), 1)
        t_id, j_str = emitted[0]
        self.assertEqual(t_id, "t2")
        self.assertIn("Dungeon Master", j_str)
        self.assertIn("Te mueves con sigilo.", j_str)

    def test_state_updated_signal(self):
        emitted = []
        self.listener.state_updated.connect(lambda j_str: emitted.append(j_str))

        ui_state = UIStateProjection(
            player_name="Aventurero",
            gold=50,
            current_location="Plaza",
            formatted_time="Día 1, 10:00",
        )
        self.listener.on_state_updated(ui_state.model_dump_json())

        self.assertEqual(len(emitted), 1)
        j_str = emitted[0]
        self.assertIn("Aventurero", j_str)
        self.assertIn('"gold":50', j_str)

    def test_task_error_signal(self):
        emitted = []
        self.listener.task_error.connect(
            lambda t_id, msg, code: emitted.append((t_id, msg, code))
        )

        self.listener.on_error("t3", "Fallo de conexión", "ConnectionError")

        self.assertEqual(len(emitted), 1)
        t_id, msg, code = emitted[0]
        self.assertEqual(t_id, "t3")
        self.assertEqual(msg, "Fallo de conexión")
        self.assertEqual(code, "ConnectionError")


if __name__ == "__main__":
    unittest.main()
