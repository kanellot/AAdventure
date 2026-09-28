"""Pruebas unitarias para los modelos de dominio canónicos de LoreBlock (type, action, conditions)."""

import unittest
from domains.lore import EntityCondition, LoreBlock, LoreEffects, ConditionGroup


class TestLoreCanonicalDomain(unittest.TestCase):
    """Verifica los atributos canónicos de type, action, elapsed_time y conditions."""

    def test_default_type(self):
        """Un LoreBlock sin type especificado asume por defecto 'Event'."""
        lb = LoreBlock(id="lb_01", name="Bloque de prueba")
        self.assertEqual(lb.type, "Event")

    def test_explicit_types(self):
        """Verifica la asignación de los tipos estructurales y de eventos (incluyendo popup)."""
        types = ["Chapter", "Quest", "Task", "Event", "popup"]
        for t in types:
            lb = LoreBlock(id=f"lb_{t.lower()}", name=f"Bloque {t}", type=t)
            self.assertEqual(lb.type, t)

    def test_strict_type_validation(self):
        """Verifica que el type 'popup' sea válido y que tipos obsoletos o no definidos sean rechazados."""
        from pydantic import ValidationError
        lb = LoreBlock(id="lb_p3", name="Alerta 3", type="popup")
        self.assertEqual(lb.type, "popup")

        with self.assertRaises(ValidationError):
            LoreBlock(id="lb_inv", name="Inválido", type="popup_event")

    def test_effects_action_and_elapsed_time(self):
        """Verifica los atributos action ('push'/'hook'), elapsed_time y bypass_llm en LoreEffects."""
        eff_push = LoreEffects(action="push", elapsed_time="01:30", bypass_llm=True, directive="Direct text")
        self.assertEqual(eff_push.action, "push")
        self.assertEqual(eff_push.elapsed_time, "01:30")
        self.assertTrue(eff_push.bypass_llm)

        eff_hook = LoreEffects(action="hook", elapsed_time="00:00", bypass_llm=False)
        self.assertEqual(eff_hook.action, "hook")
        self.assertEqual(eff_hook.elapsed_time, "00:00")
        self.assertFalse(eff_hook.bypass_llm)

    def test_condition_group_and_subconditions(self):
        """Verifica grupos de condiciones y subcondiciones."""
        c_all = EntityCondition(entity_type="loreblock", entity_id="q_01", sub_condition="all_children_done")
        self.assertEqual(c_all.sub_condition, "all_children_done")

        c_time = EntityCondition(entity_type="time", entity_id="", sub_condition="time_range", value=[100, 300])
        self.assertEqual(c_time.entity_type, "time")
        self.assertEqual(c_time.value, [100, 300])

        c_aff = EntityCondition(entity_type="npc", entity_id="npc_guard", sub_condition="affinity_range", value=[0.4, 0.8])
        self.assertEqual(c_aff.sub_condition, "affinity_range")

        c_vis = EntityCondition(entity_type="place", entity_id="cueva", sub_condition="visible")
        self.assertEqual(c_vis.sub_condition, "visible")

        group = ConditionGroup(
            conditions=[c_all, c_vis],
            rag_enabled=True,
            trigger_phrases=["¿qué debo hacer?", "guíame"],
        )
        self.assertEqual(len(group.conditions), 2)
        self.assertTrue(group.rag_enabled)
        self.assertEqual(len(group.trigger_phrases), 2)


if __name__ == "__main__":
    unittest.main()
