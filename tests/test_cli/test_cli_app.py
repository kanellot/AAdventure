"""Pruebas unitarias para la interfaz de consola interactiva CLI."""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from cli.app import CLIApp
from cli.formatter import CLIFormatter
from domains.projections import (
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnResultProjection,
)
from engines import AdventureSession


class TestCLIApp(unittest.TestCase):
    """Verifica el análisis de comandos, interacción con AdventureSession y modo verbose del CLI."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.session = AdventureSession.start_for_testing(self.aad_path)
        self.app = CLIApp(self.session, verbose=False)

    def tearDown(self):
        self.session.close()

    def test_parse_command_action_simulation(self):
        # Simulación de botones UI
        cmd, target = self.app.parse_command("/MOVE Calle Pobre")
        self.assertEqual(cmd, "MOVE")
        self.assertEqual(target, "Calle Pobre")

        cmd, target = self.app.parse_command("/look Plaza Mayor")
        self.assertEqual(cmd, "LOOK")
        self.assertEqual(target, "Plaza Mayor")

        cmd, target = self.app.parse_command("/TALK Tabernero")
        self.assertEqual(cmd, "TALK")
        self.assertEqual(target, "Tabernero")

    def test_parse_command_special_and_exit(self):
        for exit_cmd in ["/exit", "/QUIT", "/q", "exit", "quit", "q"]:
            cmd, _ = self.app.parse_command(exit_cmd)
            self.assertEqual(cmd, "EXIT")

        cmd, _ = self.app.parse_command("/help")
        self.assertEqual(cmd, "HELP")

        cmd, _ = self.app.parse_command("/status")
        self.assertEqual(cmd, "STATUS")

        cmd, _ = self.app.parse_command("/actions")
        self.assertEqual(cmd, "ACTIONS")

    def test_parse_command_free_text_message(self):
        cmd, text = self.app.parse_command("Hola, ¿tienes información sobre el mapa?")
        self.assertEqual(cmd, "MESSAGE")
        self.assertEqual(text, "Hola, ¿tienes información sobre el mapa?")

        cmd, text = self.app.parse_command("   ")
        self.assertEqual(cmd, "EMPTY")

    def test_handle_input_move_action(self):
        res = self.app.handle_input("/MOVE Calle Pobre")
        self.assertIsNotNone(res)
        self.assertIsInstance(res, TurnResultProjection)
        self.assertEqual(res.author, "Dungeon Master")
        self.assertEqual(self.session.get_ui_state().current_location, "Calle Pobre")

    def test_handle_input_action_without_target(self):
        # No debe lanzar excepción, imprime advertencia y devuelve None
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            res = self.app.handle_input("/MOVE")
        self.assertIsNone(res)
        self.assertIn("Debes especificar un objetivo", captured.getvalue())

    def test_handle_input_free_message_discrepancy(self):
        # En modo EXPLORE, send_message devuelve la proyección del sistema informando de la discrepancia
        res = self.app.handle_input("¿Alguien me ayuda?")
        self.assertIsNotNone(res)
        self.assertEqual(res.author, "SYSTEM")
        self.assertIn("EXPLORE", res.msg)

    def test_handle_input_exit(self):
        self.assertTrue(self.app.is_running)
        res = self.app.handle_input("/EXIT")
        self.assertIsNone(res)
        self.assertFalse(self.app.is_running)

    def test_verbose_formatter_output(self):
        turn_res = TurnResultProjection(
            author="Dungeon Master",
            msg="El camino se estrecha entre las viejas casas.",
            info_msg="Tiempo transcurrido: 2 min.",
            debug_prompt="SYS: Eres el Dungeon Master...\nUSER: /MOVE Calle Pobre",
            debug_structured_response='{"msg": "El camino se estrecha..."}',
            rag_evaluation=RagEvaluationProjection(
                player_input="ir hacia la taberna",
                threshold=0.65,
                matched_lore_id="lb_01",
                matched_antenna="quiero cerveza",
                injected_directive="El tabernero ofrece una jarra gratis.",
                antennas=[
                    RagAntennaScoreProjection(
                        antenna="quiero cerveza",
                        lore_id="lb_01",
                        lore_title="Misión del Tabernero",
                        score=0.82,
                        threshold=0.65,
                        conditions_met=True,
                        is_matched=True,
                        is_injected=True,
                    )
                ],
            ),
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            CLIFormatter.print_turn_result(turn_res)
            CLIFormatter.print_verbose_debug(
                turn_result=turn_res,
                game_state=self.session.get_game_state(),
                lore_graph=self.session.get_lore_graph(),
            )

        output = captured.getvalue()
        self.assertIn("Dungeon Master", output)
        self.assertIn("DEBUG MODE -v", output)
        self.assertIn("PROMPT ENVIADO AL LLM", output)
        self.assertIn("EVALUACION SEMANTICA RAG", output)
        self.assertIn("ESTADO HSM LOREBLOCKS", output)
        self.assertIn("GAME STATE SNAPSHOT", output)
        self.assertIn("RESPUESTA DEL MODELO (LLM)", output)


if __name__ == "__main__":
    unittest.main()
