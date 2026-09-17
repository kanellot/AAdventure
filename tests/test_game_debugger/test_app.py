"""Pruebas unitarias para GameDebuggerApp."""

import unittest
import os
from PySide6.QtWidgets import QApplication
from domains import TurnResultProjection
from engines.game.engine import GameEngine
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.engine import TransformerEngine
from game_debugger.app import GameDebuggerApp


class MockNarratorAdapter(BaseLLMAdapter):
    def generate(self, prompt: str, profile_name: str = "narrator", response_schema=None, schema_name=None):
        return {"msg": "El viaje transcurre sin contratiempos."}


class TestGameDebuggerApp(unittest.TestCase):
    """Verifica la inicialización, coordinación de pestañas y eventos de GameDebuggerApp."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)
        self.dm = TransformerEngine(MockNarratorAdapter())
        self.debugger = GameDebuggerApp(self.engine, self.dm, aad_path=self.aad_path)

    def tearDown(self):
        self.debugger.close()
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_app_initialization_and_tabs(self):
        self.assertIn("Adventure.aad", self.debugger.windowTitle())
        self.assertEqual(self.debugger.tab_widget.count(), 5)
        tab_names = [self.debugger.tab_widget.tabText(i) for i in range(5)]
        self.assertEqual(tab_names, ["Juego", "RAG", "LoreBlocks", "Prompt", "Result"])

        self.assertEqual(self.debugger.right_tab_widget.count(), 3)
        right_tab_names = [self.debugger.right_tab_widget.tabText(i) for i in range(3)]
        self.assertEqual(right_tab_names, ["Navigation", "Entities", "Game state"])

        # Verificar que el selector de objetivos del chat fue poblado
        self.assertGreater(self.debugger.chat_tab.target_combo.count(), 0)

    def test_entity_selection_sync_from_tree(self):
        self.debugger.on_entity_selected_from_tree("Calle Pobre")
        self.assertEqual(self.debugger.chat_tab.target_combo.currentText(), "Calle Pobre")

    def test_on_turn_finished_updates_ui(self):
        res = TurnResultProjection(
            author="Dungeon Master",
            msg="Llegas a una nueva zona.",
            debug_prompt="PROMPT ENVIADO",
            debug_raw_response='{"msg": "Llegas..."}',
        )

        self.debugger.on_turn_finished(res)

        self.assertIn("Llegas a una nueva zona.", self.debugger.chat_tab.chat_browser.toHtml())
        self.assertEqual(self.debugger.prompt_edit.toPlainText(), "PROMPT ENVIADO")
        self.assertEqual(self.debugger.result_tab.narrative_edit.toPlainText(), "Llegas a una nueva zona.")


if __name__ == "__main__":
    unittest.main()
