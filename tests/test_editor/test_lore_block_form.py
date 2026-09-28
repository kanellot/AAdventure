"""Pruebas unitarias para LoreBlockForm y LoreEffectDialog (editor.views.lore_block_form)."""

import unittest
from PySide6.QtWidgets import QApplication
from editor_debugger.editor.views.lore_block_form import LoreBlockForm, LoreEffectDialog
from editor_debugger.editor.views.dialogs import CreateLoreBlockDialog
from domains.lore import LoreBlock, LoreEffects, ConditionGroup, EntityCondition


class TestLoreBlockForm(unittest.TestCase):
    """Verifica el enlace bidireccional, types y controles de LoreBlockForm y LoreEffectDialog."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def setUp(self):
        self.form = LoreBlockForm()

    def test_initial_state_empty(self):
        self.form.set_lore_block(None)
        self.assertEqual(self.form.id_edit.text(), "")
        self.assertEqual(self.form.type_combo.currentData(), "Event")

    def test_set_lore_block_with_type(self):
        block = LoreBlock(
            id="cap_1",
            name="Capítulo 1",
            type="Chapter",
            description="Primer capítulo de la historia",
        )
        self.form.set_lore_block(block)

        self.assertEqual(self.form.id_edit.text(), "cap_1")
        self.assertEqual(self.form.type_combo.currentData(), "Chapter")
        self.assertIn("Capítulo", self.form.header_title.text())
        self.assertFalse(self.form.container_note_group.isHidden())
        self.assertTrue(self.form.effects_group.isHidden())

    def test_change_type_updates_block(self):
        block = LoreBlock(
            id="quest_goblin",
            name="Derrotar Trasgos",
            type="Quest",
        )
        self.form.set_lore_block(block)
        self.assertEqual(self.form.type_combo.currentData(), "Quest")
        self.assertIn("Quest", self.form.header_title.text())

        # Cambiar a Task
        idx_task = self.form.type_combo.findData("Task")
        self.assertGreaterEqual(idx_task, 0)
        self.form.type_combo.setCurrentIndex(idx_task)

        self.assertEqual(self.form.lore_block.type, "Task")
        self.assertIn("Tarea", self.form.header_title.text())

        # Cambiar a Event
        idx_ev = self.form.type_combo.findData("Event")
        self.assertGreaterEqual(idx_ev, 0)
        self.form.type_combo.setCurrentIndex(idx_ev)

        self.assertEqual(self.form.lore_block.type, "Event")
        self.assertTrue(self.form.container_note_group.isHidden())
        self.assertFalse(self.form.effects_group.isHidden())

        # Cambiar a popup
        idx_pop = self.form.type_combo.findData("popup")
        self.assertGreaterEqual(idx_pop, 0)
        self.form.type_combo.setCurrentIndex(idx_pop)

        self.assertEqual(self.form.lore_block.type, "popup")
        self.assertIn("Pop-up", self.form.header_title.text())
        self.assertFalse(self.form.container_note_group.isHidden())
        self.assertTrue(self.form.effects_group.isHidden())
        self.assertTrue(self.form.done_box.isHidden())
        self.assertEqual(self.form.lore_block.effects, [])
        self.assertEqual(self.form.lore_block.done_conditions, [])

    def test_card_mutations_formatting_badges(self):
        eff = LoreEffects(
            directive="¡Atención aldeanos!",
            action="hook",
            bypass_llm=True,
            gold_delta=50,
            elapsed_time="01:30",
            unlock_places=["p_bosque"],
            block_places=["p_cueva"],
            unblock_places=["p_plaza"],
        )
        tags = self.form._format_card_mutations(eff)
        self.assertIn("💰 +50 Oro", tags)
        self.assertIn("⚡ Bypass LLM", tags)
        self.assertIn("📍 Revelar p_bosque", tags)
        self.assertIn("🚫 p_cueva", tags)
        self.assertIn("🔓 p_plaza", tags)

    def test_effect_dialog_action_and_elapsed_time(self):
        eff = LoreEffects(
            directive="Direct text",
            action="hook",
            bypass_llm=True,
            elapsed_time="02:15",
            gold_delta=-20,
            affinity_delta=0.25,
            give_items=["obj_llave"],
            take_items=["obj_moneda"],
            unlock_places=["p_castillo"],
            unlock_npcs=["npc_guardia"],
            unlock_items=["obj_cofre"],
            block_places=["p_salida"],
            unblock_places=["p_entrada"],
        )
        dlg = LoreEffectDialog(effect=eff)
        self.assertTrue(dlg.bypass_llm_check.isChecked())
        self.assertEqual(dlg.action_combo.currentData(), "hook")
        self.assertEqual(dlg.time_hours_spin.value(), 2)
        self.assertEqual(dlg.time_mins_spin.value(), 15)

        # Modificar valores en el diálogo
        idx_push = dlg.action_combo.findData("push")
        dlg.action_combo.setCurrentIndex(idx_push)
        dlg.time_hours_spin.setValue(0)
        dlg.time_mins_spin.setValue(45)

        saved = dlg.get_effect()
        self.assertEqual(saved.action, "push")
        self.assertEqual(saved.elapsed_time, "00:45")
        self.assertEqual(saved.gold_delta, -20)
        self.assertAlmostEqual(saved.affinity_delta, 0.25)
        self.assertEqual(saved.give_items, ["obj_llave"])
        self.assertEqual(saved.unlock_places, ["p_castillo"])
        self.assertEqual(saved.unlock_npcs, ["npc_guardia"])
        self.assertEqual(saved.unlock_items, ["obj_cofre"])
        self.assertEqual(saved.block_places, ["p_salida"])
        self.assertEqual(saved.unblock_places, ["p_entrada"])

    def test_active_and_done_conditions_groups(self):
        cond1 = EntityCondition(entity_type="item", entity_id="obj_espada", sub_condition="have")
        cond2 = EntityCondition(entity_type="npc", entity_id="npc_mara", sub_condition="talk")

        block = LoreBlock(
            id="lb_test",
            name="Test Conditions",
            type="Event",
            active_conditions=[
                ConditionGroup(
                    conditions=[cond1],
                    rag_enabled=True,
                    trigger_phrases=["¿dónde está la espada?"],
                )
            ],
            done_conditions=[
                ConditionGroup(
                    conditions=[cond2],
                    rag_enabled=False,
                    trigger_phrases=[],
                )
            ],
        )

        self.form.set_lore_block(block)

        self.assertEqual(len(self.form.active_conditions_widget.get_conditions()), 1)
        self.assertEqual(self.form.active_conditions_widget.get_conditions()[0].entity_id, "obj_espada")
        self.assertTrue(self.form.rag_active_check.isChecked())
        self.assertIn("espada", self.form.phrases_active_edit.toPlainText())

        self.assertEqual(len(self.form.done_conditions_widget.get_conditions()), 1)
        self.assertEqual(self.form.done_conditions_widget.get_conditions()[0].entity_id, "npc_mara")
        self.assertFalse(self.form.rag_done_check.isChecked())

    def test_create_lore_block_dialog_popup_type(self):
        dlg = CreateLoreBlockDialog(default_type="popup", parent_id="lb_padre")
        self.assertEqual(dlg.type_combo.currentData(), "popup")
        dlg.title_edit.setText("Alerta Roja")
        title, type_val, pid = dlg.get_data()
        self.assertEqual(title, "Alerta Roja")
        self.assertEqual(type_val, "popup")
        self.assertEqual(pid, "lb_padre")


if __name__ == "__main__":
    unittest.main()

