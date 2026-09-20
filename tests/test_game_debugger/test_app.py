"""Pruebas unitarias para GameDebuggerApp."""

import unittest
import os
from PySide6.QtWidgets import QApplication
from domains import TurnResultProjection
from domains.projections import UIStateProjection
from engines import AdventureSession
from engines.transformer.base_adapter import BaseLLMAdapter
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
        self.session = AdventureSession.start_for_testing(
            self.aad_path,
            llm_adapter=MockNarratorAdapter(),
        )
        self.debugger = GameDebuggerApp(session=self.session, aad_path=self.aad_path)

    def tearDown(self):
        self.debugger.close()

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

    def test_reactive_slots_update_ui(self):
        from engines.events import ThinkingEvent
        # 1. Probar on_thinking_changed(True)
        event_true = ThinkingEvent(task_id="t1", is_thinking=True, action="MOVE", message="Caminando...")
        self.debugger.on_thinking_changed(event_true.model_dump_json())
        self.assertFalse(self.debugger.chat_tab.spinner.isHidden())
        self.assertIn("Caminando...", self.debugger.chat_tab.lbl_thinking.text())

        # 2. Probar on_task_completed
        res = TurnResultProjection(
            author="Dungeon Master",
            msg="Has llegado a la taberna.",
            debug_prompt="PROMPT REACTIVO",
            debug_raw_response="{}",
        )
        self.debugger.on_task_completed("t1", res.model_dump_json())
        self.assertIn("Has llegado a la taberna.", self.debugger.chat_tab.chat_browser.toHtml())
        self.assertEqual(self.debugger.prompt_edit.toPlainText(), "PROMPT REACTIVO")
        self.assertEqual(self.debugger.result_tab.narrative_edit.toPlainText(), "Has llegado a la taberna.")

        # 3. Probar on_state_updated
        ui_state = self.session.get_ui_state()
        self.debugger.on_state_updated(ui_state.model_dump_json())
        self.assertIn("Jugador:", self.debugger.statusBar().currentMessage())

        # 4. Probar on_thinking_changed(False)
        event_false = ThinkingEvent(task_id="t1", is_thinking=False)
        self.debugger.on_thinking_changed(event_false.model_dump_json())
        self.assertTrue(self.debugger.chat_tab.spinner.isHidden())


if __name__ == "__main__":
    unittest.main()
