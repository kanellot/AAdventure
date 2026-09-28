"""Pruebas unitarias e integradas para la suite EditorDebuggerApp."""

import os
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from editor_debugger.app import EditorDebuggerApp


class TestEditorDebuggerSuite(unittest.TestCase):
    """Verifica el ciclo de vida, navegación por pestañas y desacoplamiento en EditorDebuggerApp."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def tearDown(self):
        # Asegurar limpieza de ventanas y sesiones tras cada test
        if hasattr(self, "suite") and self.suite:
            try:
                if self.suite.editor_app and self.suite.editor_app.controller:
                    self.suite.editor_app.controller.is_dirty = False
                if self.suite.debugger_app and hasattr(self.suite.debugger_app, "session") and self.suite.debugger_app.session:
                    self.suite.debugger_app.session.close()
                self.suite.close()
            except Exception:
                pass

    def test_suite_initialization_editor_mode(self):
        """Comprueba el inicio predeterminado en modo Editor."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.assertEqual(self.suite.tab_widget.count(), 2)
        self.assertEqual(self.suite.tab_widget.tabText(0), "✏️ Editor de Historias")
        self.assertEqual(self.suite.tab_widget.tabText(1), "🐞 Depurador de Juego")
        self.assertEqual(self.suite.tab_widget.currentIndex(), 0)
        self.assertIn("Editor de Historias", self.suite.windowTitle())
        self.assertIsNotNone(self.suite.editor_app)

    def test_suite_initialization_debugger_mode(self):
        """Comprueba el inicio directo en modo Depurador."""
        self.suite = EditorDebuggerApp(mode="debugger", aad_path=self.aad_path)
        self.assertEqual(self.suite.tab_widget.count(), 2)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 1)
        self.assertIn("Depurador de Juego", self.suite.windowTitle())
        self.assertIsNotNone(self.suite.debugger_app)

    def test_tab_switching_updates_title_and_debugger(self):
        """Verifica la conmutación de pestañas y la inicialización reactiva del depurador."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 0)

        # Cambiar a Depurador
        self.suite.tab_widget.setCurrentIndex(1)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 1)
        self.assertIsNotNone(self.suite.debugger_app)
        self.assertIn("Depurador de Juego", self.suite.windowTitle())

        # Volver al Editor
        self.suite.tab_widget.setCurrentIndex(0)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 0)
        self.assertIn("Editor de Historias", self.suite.windowTitle())

    def test_detachment_and_reattachment_cycle(self):
        """Valida el desacople del depurador a ventana flotante y su posterior reacople."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()

        # 1. Desacoplar
        self.suite.detach_debugger()
        self.assertIsNotNone(self.suite.floating_window)
        self.assertIn("Reacoplar", self.suite.detach_btn.text())

        # 2. Reacoplar
        self.suite.reattach_debugger()
        self.assertIsNone(self.suite.floating_window)
        self.assertIn("Desacoplar", self.suite.detach_btn.text())
        self.assertEqual(self.suite.tab_widget.count(), 2)

    def test_dirty_flag_and_has_unsaved_changes(self):
        """Verifica que el flag is_dirty y has_unsaved_changes operen adecuadamente."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.assertFalse(self.suite.editor_app.has_unsaved_changes())

        # Marcar cambio
        self.suite.editor_app.controller.is_dirty = True
        self.assertTrue(self.suite.editor_app.has_unsaved_changes())

    def test_eager_initialization_and_game_persistence_across_tabs(self):
        """Valida que ambos subsistemas se inicializan al arranque y la partida persiste al cambiar pestañas."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        # 1. Ambos componentes deben estar listos al inicio
        self.assertIsNotNone(self.suite.editor_app)
        self.assertIsNotNone(self.suite.debugger_app)
        self.assertEqual(self.suite.tab_widget.count(), 2)

        # 2. Iniciar la partida en el depurador y mutar estado de juego (simular avance)
        self.suite.start_debugger_adventure()
        debugger = self.suite.debugger_app
        initial_loc = debugger.engine.game_state_controller.game_state.current_location
        initial_gold = debugger.engine.game_state_controller.game_state.gold
        # Modificar oro de la partida
        debugger.engine.game_state_controller.game_state.gold += 50

        # 3. Cambiar a la pestaña Editor
        self.suite.tab_widget.setCurrentIndex(0)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 0)

        # 4. Volver a la pestaña Depurador
        self.suite.tab_widget.setCurrentIndex(1)
        self.assertEqual(self.suite.tab_widget.currentIndex(), 1)

        # 5. La partida debe ser la misma instancia y conservar el estado mutado
        self.assertIs(self.suite.debugger_app, debugger)
        self.assertEqual(self.suite.debugger_app.engine.game_state_controller.game_state.gold, initial_gold + 50)
        self.assertEqual(self.suite.debugger_app.engine.game_state_controller.game_state.current_location, initial_loc)
        self.assertFalse(self.suite.debugger_app.session.is_closed)

    def test_start_and_stop_buttons_present_and_cycle(self):
        """Verifica la existencia y ciclo de activación de los botones Recargar, Start (▶) y Stop (■)."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()

        # 1. Verificar existencia y símbolos
        self.assertTrue(hasattr(self.suite, "reload_btn"))
        self.assertTrue(hasattr(self.suite, "start_btn"))
        self.assertTrue(hasattr(self.suite, "stop_btn"))
        self.assertIn("🔄", self.suite.reload_btn.text())
        self.assertIn("▶", self.suite.start_btn.text())
        self.assertIn("■", self.suite.stop_btn.text())

        # 2. Estado inicial: el depurador arranca en STOP por defecto
        self.assertTrue(self.suite.start_btn.isEnabled())
        self.assertFalse(self.suite.stop_btn.isEnabled())
        self.assertTrue(self.suite.reload_btn.isEnabled())
        self.assertFalse(self.suite.debugger_app.is_running)

        # 3. Iniciar la partida con Start
        self.suite.start_debugger_adventure()
        self.assertFalse(self.suite.start_btn.isEnabled())
        self.assertTrue(self.suite.stop_btn.isEnabled())
        self.assertTrue(self.suite.debugger_app.is_running)
        self.assertFalse(self.suite.debugger_app.session.is_closed)

        # 4. Detener la partida con Stop
        self.suite.stop_debugger_adventure()
        self.assertTrue(self.suite.start_btn.isEnabled())
        self.assertFalse(self.suite.stop_btn.isEnabled())
        self.assertFalse(self.suite.debugger_app.is_running)
        self.assertTrue(self.suite.debugger_app.session.is_closed)

    def test_reload_button_saves_and_starts_adventure(self):
        """Verifica que el botón Recargar guarda los cambios del editor e inicia el depurador."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()

        # Marcar cambios pendientes en el editor
        self.suite.editor_app.controller.is_dirty = True
        self.assertTrue(self.suite.editor_app.has_unsaved_changes())

        # El depurador arranca en STOP
        self.assertFalse(self.suite.debugger_app.is_running)

        # Pulsar botón de recarga (Guardar + Play)
        self.suite.reload_and_play_debugger()

        # Los cambios deben haber quedado guardados y el depurador en ejecución
        self.assertFalse(self.suite.editor_app.has_unsaved_changes())
        self.assertTrue(self.suite.debugger_app.is_running)
        self.assertFalse(self.suite.start_btn.isEnabled())
        self.assertTrue(self.suite.stop_btn.isEnabled())

    def test_editor_load_story_synchronizes_debugger_and_stops(self):
        """Verifica que al cargar una nueva historia en el editor, el depurador se sincroniza y queda en STOP."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()

        # Iniciar partida previa en el depurador
        self.suite.start_debugger_adventure()
        self.assertTrue(self.suite.debugger_app.is_running)

        # Cargar otra historia en el editor (usamos la misma ruta para comprobar el evento)
        self.suite.editor_app.load_story_file(self.aad_path)

        # El depurador debe detenerse y quedar en STOP por defecto
        self.assertFalse(self.suite.debugger_app.is_running)
        self.assertTrue(self.suite.start_btn.isEnabled())
        self.assertFalse(self.suite.stop_btn.isEnabled())
        self.assertEqual(self.suite.debugger_app.aad_path, self.aad_path)

    def test_editor_new_story_synchronizes_debugger_and_stops(self):
        """Verifica que al crear una nueva historia en el editor, el depurador se vacía y queda en STOP."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()

        # Iniciar partida previa en el depurador
        self.suite.start_debugger_adventure()
        self.assertTrue(self.suite.debugger_app.is_running)

        # Crear nueva historia
        self.suite.editor_app.on_new_story()

        # El depurador debe detenerse y quedar en STOP
        self.assertFalse(self.suite.debugger_app.is_running)
        self.assertTrue(self.suite.start_btn.isEnabled())
        self.assertFalse(self.suite.stop_btn.isEnabled())
        self.assertEqual(self.suite.debugger_app.aad_path, "")

    def test_floating_window_has_reload_button_and_syncs_state(self):
        """Verifica que la ventana flotante dispone del botón Recargar y sincroniza los estados."""
        self.suite = EditorDebuggerApp(mode="editor", aad_path=self.aad_path)
        self.suite._ensure_debugger_initialized()
        self.suite.detach_debugger()

        floating = self.suite.floating_window
        self.assertIsNotNone(floating)
        self.assertTrue(hasattr(floating, "reload_btn"))
        self.assertTrue(hasattr(floating, "start_btn"))
        self.assertTrue(hasattr(floating, "stop_btn"))

        # Inicialmente en STOP
        self.assertTrue(floating.start_btn.isEnabled())
        self.assertFalse(floating.stop_btn.isEnabled())
        self.assertTrue(floating.reload_btn.isEnabled())

        # Iniciar desde ventana flotante
        floating.start_btn.click()
        self.assertTrue(self.suite.debugger_app.is_running)
        self.assertFalse(floating.start_btn.isEnabled())
        self.assertTrue(floating.stop_btn.isEnabled())

        # Detener desde ventana flotante
        floating.stop_btn.click()
        self.assertFalse(self.suite.debugger_app.is_running)
        self.assertTrue(floating.start_btn.isEnabled())
        self.assertFalse(floating.stop_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
