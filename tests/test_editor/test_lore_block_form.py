"""Pruebas unitarias para LoreBlockForm y LoreEffectDialog (editor.views.lore_block_form)."""

import unittest
from PySide6.QtWidgets import QApplication
from editor.views.lore_block_form import LoreBlockForm, LoreEffectDialog
from domains.lore import LoreBlock, LoreEffects


class TestLoreBlockForm(unittest.TestCase):
    """Verifica el enlace bidireccional, presets y controles de LoreBlockForm y LoreEffectDialog."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def setUp(self):
        self.form = LoreBlockForm()

    def test_initial_state_empty(self):
        self.form.set_lore_block(None)
        self.assertEqual(self.form.id_edit.text(), "")
        self.assertEqual(self.form.preset_combo.currentData(), "event")

    def test_set_lore_block_with_preset(self):
        block = LoreBlock(
            id="cap_1",
            name="Capítulo 1",
            preset="chapter",
            description="Primer capítulo de la historia",
        )
        self.form.set_lore_block(block)

        self.assertEqual(self.form.id_edit.text(), "cap_1")
        self.assertEqual(self.form.preset_combo.currentData(), "chapter")
        self.assertIn("Capítulo", self.form.header_title.text())

    def test_change_preset_updates_block(self):
        block = LoreBlock(
            id="quest_goblin",
            name="Derrotar Trasgos",
            preset="quest",
        )
        self.form.set_lore_block(block)
        self.assertEqual(self.form.preset_combo.currentData(), "quest")
        self.assertIn("Quest", self.form.header_title.text())

        # Cambiar a task
        idx_task = self.form.preset_combo.findData("task")
        self.assertGreaterEqual(idx_task, 0)
        self.form.preset_combo.setCurrentIndex(idx_task)

        self.assertEqual(self.form.lore_block.preset, "task")
        self.assertIn("Tarea", self.form.header_title.text())

    def test_card_mutations_formatting_badges(self):
        eff = LoreEffects(
            directive="¡Atención aldeanos!",
            execution_mode="hook",
            bypass_llm=True,
            gold_delta=50,
        )
        tags = self.form._format_card_mutations(eff)
        self.assertIn("💰 +50 Oro", tags)
        self.assertIn("⚡ Bypass LLM", tags)
        self.assertIn("🎧 Hook", tags)

    def test_effect_dialog_bypass_llm_and_exec_mode(self):
        eff = LoreEffects(
            directive="Direct text",
            execution_mode="hook",
            bypass_llm=True,
        )
        dlg = LoreEffectDialog(effect=eff)
        self.assertTrue(dlg.bypass_llm_check.isChecked())
        self.assertEqual(dlg.exec_mode_combo.currentData(), "hook")
        # En modo hook, force_check debe estar deshabilitado
        self.assertFalse(dlg.force_check.isEnabled())

        # Cambiar a push
        idx_push = dlg.exec_mode_combo.findData("push")
        dlg.exec_mode_combo.setCurrentIndex(idx_push)
        self.assertTrue(dlg.force_check.isEnabled())

        # Probar guardado
        dlg.bypass_llm_check.setChecked(False)
        saved = dlg.get_effect()
        self.assertEqual(saved.execution_mode, "push")
        self.assertFalse(saved.bypass_llm)


if __name__ == "__main__":
    unittest.main()
