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
        # En modo hook, auto_panel debe estar oculto
        self.assertTrue(dlg.auto_panel.isHidden())

        # Cambiar a push
        idx_push = dlg.exec_mode_combo.findData("push")
        dlg.exec_mode_combo.setCurrentIndex(idx_push)
        self.assertFalse(dlg.auto_panel.isHidden())

        # Probar guardado
        dlg.bypass_llm_check.setChecked(False)
        saved = dlg.get_effect()
        self.assertEqual(saved.execution_mode, "push")
        self.assertTrue(saved.force_action)
        self.assertFalse(saved.bypass_llm)

    def test_preset_adaptation_event_popup(self):
        block = LoreBlock(
            id="popup_intro",
            name="Aviso inicial",
            preset="event_popup",
        )
        self.form.set_lore_block(block)

        self.assertFalse(self.form.popup_group.isHidden())
        self.assertTrue(self.form.effects_group.isHidden())
        self.assertTrue(self.form.container_note_group.isHidden())
        self.assertTrue(self.form.active_rag_box.isHidden())

        self.form.popup_text_edit.setPlainText("¡Bienvenido al calabozo!")
        self.assertEqual(block.on_active.directive, "¡Bienvenido al calabozo!")
        self.assertTrue(block.on_active.bypass_llm)
        self.assertEqual(block.on_active.execution_mode, "push")

    def test_preset_adaptation_chapter_quest_task(self):
        for p in ("chapter", "quest", "task"):
            block = LoreBlock(id=f"{p}_1", name=f"Test {p}", preset=p)
            self.form.set_lore_block(block)

            self.assertFalse(self.form.container_note_group.isHidden(), f"Fallo en preset {p}")
            self.assertTrue(self.form.effects_group.isHidden(), f"Fallo en preset {p}")
            self.assertTrue(self.form.popup_group.isHidden(), f"Fallo en preset {p}")
            self.assertTrue(self.form.active_rag_box.isHidden(), f"Fallo en preset {p}")
            self.assertFalse(self.form.desc_group.isHidden(), f"Fallo en preset {p}")

    def test_preset_adaptation_event_diag(self):
        block = LoreBlock(id="diag_1", name="Diálogo tabernero", preset="event_diag")
        self.form.set_lore_block(block)

        self.assertFalse(self.form.effects_group.isHidden())
        self.assertFalse(self.form.active_rag_box.isHidden())
        self.assertTrue(self.form.popup_group.isHidden())
        self.assertTrue(self.form.container_note_group.isHidden())
        self.assertEqual(self.form._get_allowed_target_types_for_current_preset(), ["npc"])

    def test_preset_adaptation_event_look(self):
        block = LoreBlock(id="look_1", name="Inspección altar", preset="event_look")
        self.form.set_lore_block(block)

        self.assertFalse(self.form.effects_group.isHidden())
        self.assertFalse(self.form.active_rag_box.isHidden())
        self.assertTrue(self.form.popup_group.isHidden())
        self.assertTrue(self.form.container_note_group.isHidden())
        self.assertEqual(self.form._get_allowed_target_types_for_current_preset(), ["place", "item"])


if __name__ == "__main__":
    unittest.main()
