"""Pruebas unitarias para CLIEventListener."""

import io
import unittest
from unittest.mock import MagicMock, patch

from cli.listener import CLIEventListener
from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import ThinkingEvent


class TestCLIEventListener(unittest.TestCase):
    """Verifica la recepción y renderizado de eventos en CLIEventListener."""

    def setUp(self):
        self.mock_session = MagicMock()
        self.listener = CLIEventListener(session=self.mock_session, verbose=False)

    def test_on_thinking_changed_lore(self):
        evt = ThinkingEvent(task_id="t_lore", is_thinking=True, action="TALK", target="Tabernero", source="LORE")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            self.listener.on_thinking_changed(evt.model_dump_json())
        self.assertIn("Simulación LoreBlock en curso", captured.getvalue())

    def test_on_task_completed_normal_and_popup(self):
        res = TurnResultProjection(
            author="Dungeon Master",
            msg="El camino está despejado.",
            popup_message="¡Has encontrado un cofre secreto!",
            popup_title="Cofre Abierto",
        )
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            self.listener.on_task_completed("t1", res.model_dump_json())
        output = captured.getvalue()
        self.assertIn("El camino está despejado.", output)
        self.assertIn("COFRE ABIERTO", output)
        self.assertIn("¡Has encontrado un cofre secreto!", output)
        self.assertEqual(self.listener.latest_turn_result, res)

    def test_on_state_updated(self):
        state = UIStateProjection(player_name="Aventurero", gold=50, current_location="Plaza Mayor", formatted_time="08:30", game_state="EXPLORE")
        self.listener.on_state_updated(state.model_dump_json())
        self.assertEqual(self.listener.latest_ui_state, state)

    def test_on_error(self):
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            self.listener.on_error("t1", "Fallo de prueba", "ValueError")
        self.assertIn("[SYSTEM ERROR] ValueError: Fallo de prueba", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
