"""Pruebas unitarias para TurnWorker del depurador."""

import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from domains import ActionCommand, TurnResultProjection
from game_debugger.worker import TurnWorker


class TestTurnWorker(unittest.TestCase):
    """Verifica la ejecución asíncrona de turnos y captura de errores en TurnWorker."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def test_turn_worker_success(self):
        mock_engine = MagicMock()
        mock_dm = MagicMock()
        expected_output = TurnResultProjection(
            author="Dungeon Master",
            msg="Avanzas con precaución.",
        )
        mock_engine.execute_turn.return_value = expected_output

        cmd = ActionCommand(action="MOVE", target="Calle Pobre")
        worker = TurnWorker(mock_engine, mock_dm, cmd, player_input="ir al norte")

        emitted_results = []
        worker.finished_turn.connect(emitted_results.append)

        # Ejecución síncrona de la lógica de run()
        worker.run()

        self.assertEqual(len(emitted_results), 1)
        res = emitted_results[0]
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "Dungeon Master")
        self.assertEqual(res.msg, "Avanzas con precaución.")
        mock_engine.execute_turn.assert_called_once_with(cmd, player_input="ir al norte", dm=mock_dm)

    def test_turn_worker_handles_exception(self):
        mock_engine = MagicMock()
        mock_dm = MagicMock()
        mock_engine.execute_turn.side_effect = RuntimeError("Fallo de conexión LLM")

        cmd = ActionCommand(action="TALK", target="npc_tabernero")
        worker = TurnWorker(mock_engine, mock_dm, cmd, player_input="hola")

        emitted_results = []
        worker.finished_turn.connect(emitted_results.append)

        worker.run()

        self.assertEqual(len(emitted_results), 1)
        res = emitted_results[0]
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "SYSTEM")
        self.assertIn("Fallo de conexión LLM", res.msg)

    def test_turn_worker_with_session_action(self):
        mock_session = MagicMock()
        mock_session.execute_action.return_value = TurnResultProjection(
            author="Dungeon Master",
            msg="Te mueves al sur.",
        )

        worker = TurnWorker(session=mock_session, action="MOVE", target="Plaza Mayor")
        emitted_results = []
        worker.finished_turn.connect(emitted_results.append)
        worker.run()

        self.assertEqual(len(emitted_results), 1)
        self.assertEqual(emitted_results[0].msg, "Te mueves al sur.")
        mock_session.execute_action.assert_called_once_with("MOVE", "Plaza Mayor")

    def test_turn_worker_with_session_message(self):
        mock_session = MagicMock()
        mock_session.send_message.return_value = TurnResultProjection(
            author="Tabernero",
            msg="¡Saludos viajero!",
        )

        worker = TurnWorker(session=mock_session, player_input="Hola!")
        emitted_results = []
        worker.finished_turn.connect(emitted_results.append)
        worker.run()

        self.assertEqual(len(emitted_results), 1)
        self.assertEqual(emitted_results[0].msg, "¡Saludos viajero!")
        mock_session.send_message.assert_called_once_with("Hola!")


if __name__ == "__main__":
    unittest.main()

