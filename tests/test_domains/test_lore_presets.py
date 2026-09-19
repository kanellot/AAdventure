"""Pruebas unitarias para los modelos de dominio de LoreBlock presets y bypass de LLM."""

import unittest
from domains.lore import EntityCondition, LoreBlock, LoreEffects


class TestLorePresetsDomain(unittest.TestCase):
    """Verifica la definición y normalización de presets y atributos de lore."""

    def test_default_preset_normalization(self):
        """Un LoreBlock sin preset debe asumir por defecto 'event'."""
        lb = LoreBlock(id="lb_01", name="Bloque de prueba")
        self.assertEqual(lb.preset, "event")
        self.assertFalse(lb.bypass_llm)
        self.assertEqual(lb.execution_mode, "hook")

    def test_explicit_presets(self):
        """Verifica la asignación de presets estructurales y de eventos."""
        presets = ["chapter", "quest", "task", "event_diag", "event_look", "event_popup", "event"]
        for p in presets:
            lb = LoreBlock(id=f"lb_{p}", name=f"Bloque {p}", preset=p)
            self.assertEqual(lb.preset, p)

    def test_event_popup_bypass_llm_property(self):
        """Un preset 'event_popup' siempre reporta bypass_llm = True."""
        lb = LoreBlock(id="popup_01", name="Alerta", preset="event_popup")
        self.assertTrue(lb.bypass_llm)

    def test_effects_execution_mode_and_bypass_llm(self):
        """Verifica los atributos execution_mode ('push'/'hook') y bypass_llm en LoreEffects."""
        eff_push = LoreEffects(timing="active", execution_mode="push", bypass_llm=True, directive="Direct text")
        self.assertEqual(eff_push.execution_mode, "push")
        self.assertTrue(eff_push.force_action)
        self.assertTrue(eff_push.bypass_llm)

        eff_hook = LoreEffects(timing="active", execution_mode="hook", bypass_llm=False)
        self.assertEqual(eff_hook.execution_mode, "hook")
        self.assertFalse(eff_hook.bypass_llm)

    def test_loreblock_delegates_bypass_llm(self):
        """LoreBlock delega bypass_llm si alguno de sus efectos lo activa."""
        lb = LoreBlock(
            id="lb_direct",
            name="Diálogo directo",
            preset="event_diag",
            effects=[LoreEffects(timing="active", bypass_llm=True, directive="Hola viajero")],
        )
        self.assertTrue(lb.bypass_llm)

    def test_new_entity_condition_subconditions(self):
        """Verifica la instanciación de condiciones con las nuevas subcondiciones."""
        c_all = EntityCondition(entity_type="loreblock", entity_id="q_01", sub_condition="all_children_done")
        self.assertEqual(c_all.sub_condition, "all_children_done")

        c_time = EntityCondition(entity_type="time", entity_id="", sub_condition="time_range", value=[100, 300])
        self.assertEqual(c_time.entity_type, "time")
        self.assertEqual(c_time.value, [100, 300])

        c_aff = EntityCondition(entity_type="npc", entity_id="npc_guard", sub_condition="affinity_range", value=[0.4, 0.8])
        self.assertEqual(c_aff.sub_condition, "affinity_range")

        c_vis = EntityCondition(entity_type="place", entity_id="cueva", sub_condition="visible")
        self.assertEqual(c_vis.sub_condition, "visible")


if __name__ == "__main__":
    unittest.main()
