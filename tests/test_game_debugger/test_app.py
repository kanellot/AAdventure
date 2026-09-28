"""Pruebas unitarias para GameDebuggerApp."""

import unittest
import os
from PySide6.QtWidgets import QApplication
from domains.projections import (
    InventoryProjection,
    NotebookProjection,
    TurnDebugProjection,
    TurnOutput,
    TurnResultProjection,
    UIStateProjection,
    WorldMapProjection,
)
from engines import AdventureSession
from editor_debugger.debugger.app import GameDebuggerApp


class TestGameDebuggerApp(unittest.TestCase):
    """Verifica la inicialización, coordinación de pestañas y eventos de GameDebuggerApp."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.session = AdventureSession.create(self.aad_path)
        self.debugger = GameDebuggerApp(session=self.session, aad_path=self.aad_path, auto_start=True)

    def tearDown(self):
        self.debugger.close()

    def test_debugger_default_auto_start_false_is_stopped(self):
        """Verifica que sin auto_start=True, GameDebuggerApp arranca detenido en STOP."""
        session = AdventureSession.create(self.aad_path)
        debugger = GameDebuggerApp(session=session, aad_path=self.aad_path)
        try:
            self.assertFalse(debugger.is_running)
            self.assertIn("DETENIDO", debugger.chat_tab.header_state_lbl.text())
            self.assertEqual(debugger.chat_tab.target_combo.count(), 0)
        finally:
            debugger.close()

    def test_app_initialization_and_tabs(self):
        self.assertIn("Adventure.aad", self.debugger.windowTitle())
        self.assertEqual(self.debugger.tab_widget.count(), 5)
        tab_names = [self.debugger.tab_widget.tabText(i) for i in range(5)]
        self.assertEqual(tab_names, ["Juego", "RAG", "LoreBlocks", "Prompt", "Result"])

        self.assertEqual(self.debugger.right_tab_widget.count(), 4)
        right_tab_names = [self.debugger.right_tab_widget.tabText(i) for i in range(4)]
        self.assertEqual(right_tab_names, ["Map", "Entities", "Notebook", "Gamestate"])

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
            output=TurnOutput(author="Dungeon Master", msg="Has llegado a la taberna."),
            map=WorldMapProjection(),
            inventory=InventoryProjection(),
            notebook=NotebookProjection(),
            debug=TurnDebugProjection(
                prompt="PROMPT REACTIVO",
                raw_response="{}",
            ),
        )
        self.debugger.on_task_completed("t1", res.model_dump_json())
        self.assertIn("Has llegado a la taberna.", self.debugger.chat_tab.chat_browser.toHtml())
        self.assertEqual(self.debugger.prompt_edit.toPlainText(), "PROMPT REACTIVO")
        self.assertEqual(self.debugger.result_tab.narrative_edit.toPlainText(), "Has llegado a la taberna.")

        # 3. Probar on_state_updated
        ui_state = self.debugger.engine.get_ui_state_projection()
        self.debugger.on_state_updated(ui_state.model_dump_json())
        self.assertIn("Jugador:", self.debugger.statusBar().currentMessage())

        # 4. Probar on_thinking_changed(False)
        event_false = ThinkingEvent(task_id="t1", is_thinking=False)
        self.debugger.on_thinking_changed(event_false.model_dump_json())
        self.assertTrue(self.debugger.chat_tab.spinner.isHidden())

    def test_start_and_stop_adventure(self):
        """Verifica la detención y arranque de la aventura con actualización de estados."""
        signals_received = []
        self.debugger.adventure_state_changed.connect(signals_received.append)

        # 1. Detener aventura
        self.debugger.stop_adventure()
        self.assertFalse(self.debugger.is_running)
        self.assertTrue(self.debugger.session.is_closed)
        self.assertFalse(self.debugger.chat_tab.btn_move.isEnabled())
        self.assertIn("DETENIDO", self.debugger.chat_tab.header_state_lbl.text())
        self.assertEqual(self.debugger.chat_tab.target_combo.count(), 0)
        self.assertEqual(self.debugger.map_tab.topLevelItemCount(), 0)
        self.assertEqual(self.debugger.entities_tab.topLevelItemCount(), 0)
        self.assertEqual(self.debugger.notebook_tab.topLevelItemCount(), 0)
        self.assertEqual(self.debugger.prompt_edit.toPlainText(), "")
        self.assertIn(False, signals_received)

        # 2. Iniciar aventura
        self.debugger.start_adventure()
        self.assertTrue(self.debugger.is_running)
        self.assertFalse(self.debugger.session.is_closed)
        self.assertGreater(self.debugger.chat_tab.target_combo.count(), 0)
        self.assertGreater(self.debugger.map_tab.topLevelItemCount(), 0)
        self.assertIn(True, signals_received)


if __name__ == "__main__":
    unittest.main()
