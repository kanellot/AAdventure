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
        """Verifica la asignación de los 7 tipos estructurales y de eventos."""
        types = ["Chapter", "Quest", "Task", "Event", "popup", "Info", "ask_permission"]
        for t in types:
            lb = LoreBlock(id=f"lb_{t.lower()}", name=f"Bloque {t}", type=t)
            self.assertEqual(lb.type, t)

    def test_strict_type_validation(self):
        """Verifica que los 7 tipos sean válidos y que tipos obsoletos o no definidos sean rechazados."""
        from pydantic import ValidationError
        lb_info = LoreBlock(id="lb_i1", name="Pista 1", type="Info")
        self.assertEqual(lb_info.type, "Info")
        lb_ask = LoreBlock(id="lb_a1", name="Pregunta 1", type="ask_permission")
        self.assertEqual(lb_ask.type, "ask_permission")

        with self.assertRaises(ValidationError):
            LoreBlock(id="lb_inv", name="Inválido", type="popup_event")

    def test_doble_effect_and_no_repeat(self):
        """Verifica que LoreBlock soporte active_effects y done_effects nativamente y no tenga atributo repeat."""
        eff_act = LoreEffects(action="hook", directive="Contexto al entrar")
        eff_done = LoreEffects(action="push", directive="Recompensa al salir", gold_delta=20)
        lb = LoreBlock(
            id="lb_de",
            name="Doble Efecto",
            active_effects=[eff_act],
            done_effects=[eff_done],
        )
        self.assertEqual(len(lb.active_effects), 1)
        self.assertEqual(len(lb.done_effects), 1)
        self.assertFalse(hasattr(lb, "repeat"))

    def test_init_preset_loreblock_factory(self):
        """Verifica la inicialización canónica de los presets mediante init_preset_loreblock."""
        from editor_debugger.editor.constants import init_preset_loreblock

        # 1. Popup
        pop = init_preset_loreblock("popup", "pop_1", "Aviso Test")
        self.assertEqual(pop.type, "popup")
        self.assertIn("aviso emergente", pop.description.lower())
        self.assertEqual(pop.active_effects, [])
        self.assertEqual(pop.done_effects, [])

        # 2. Info
        info = init_preset_loreblock("Info", "info_1", "Pista Test", parent_id="c_1")
        self.assertEqual(info.type, "Info")
        self.assertEqual(info.parent_id, "c_1")
        self.assertEqual(len(info.active_effects), 1)
        self.assertEqual(info.active_effects[0].action, "hook")
        self.assertEqual(info.done_effects, [])

        # 3. ask_permission
        ask = init_preset_loreblock("ask_permission", "ask_1", "Pregunta Test", parent_id="t_1")
        self.assertEqual(ask.type, "ask_permission")
        self.assertEqual(ask.parent_id, "t_1")
        self.assertEqual(len(ask.active_effects), 1)
        self.assertEqual(len(ask.done_conditions), 1)
        self.assertTrue(ask.done_conditions[0].rag_enabled)
        self.assertIn("sí", ask.done_conditions[0].trigger_phrases)
        self.assertEqual(len(ask.done_effects), 1)

    def test_hierarchy_allowed_child_types_matrix(self):
        """Verifica la matriz de jerarquía estricta según ALLOWED_CHILD_TYPES."""
        from editor_debugger.editor.constants import get_allowed_child_types

        self.assertEqual(get_allowed_child_types(None), ["Chapter", "popup"])
        self.assertEqual(get_allowed_child_types(""), ["Chapter", "popup"])
        self.assertEqual(get_allowed_child_types("Chapter"), ["Quest", "Info", "popup"])
        self.assertEqual(get_allowed_child_types("Quest"), ["Task", "Info", "popup"])
        self.assertEqual(get_allowed_child_types("Task"), ["Event", "ask_permission", "Info", "popup"])
        self.assertEqual(get_allowed_child_types("Event"), ["Event", "ask_permission", "Info", "popup"])
        self.assertEqual(get_allowed_child_types("Info"), ["popup"])
        self.assertEqual(get_allowed_child_types("ask_permission"), ["popup"])
        self.assertEqual(get_allowed_child_types("popup"), [])

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

        c_aff = EntityCondition(entity_type="npc", entity_id="npc_guard", sub_condition="affinity_range",
                                value=[0.4, 0.8])
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
