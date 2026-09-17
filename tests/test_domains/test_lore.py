"""Pruebas unitarias para modelos de Lore y Condiciones HSM (domains.lore)."""

import unittest
from domains.lore import EntityCondition, LoreEffects, LoreBlock, LoreBlockState


class TestLoreModels(unittest.TestCase):
    """Pruebas de modelos de LoreBlock, LoreEffects y EntityCondition."""

    def test_entity_condition_creation_and_negation(self):
        cond = EntityCondition(
            entity_type="npc",
            entity_id="npc_tabernero",
            sub_condition="affinity",
            value=0.7,
            is_negated=False,
        )
        self.assertEqual(cond.entity_type, "npc")
        self.assertEqual(cond.entity_id, "npc_tabernero")
        self.assertEqual(cond.sub_condition, "affinity")
        self.assertEqual(cond.value, 0.7)
        self.assertFalse(cond.is_negated)

        # Inversión
        cond_neg = EntityCondition(
            entity_type="place",
            entity_id="Taberna",
            sub_condition="current_location",
            is_negated=True,
        )
        self.assertTrue(cond_neg.is_negated)

    def test_lore_effects_model(self):
        eff = LoreEffects(
            target="npc_tabernero",
            timing="active",
            directive="El tabernero te mira con recelo.",
            give_gold=50,
            give_items=["llave_bronce"],
            affinity_delta=0.1,
            force_action=True,
            trigger_action_type="TALK",
            trigger_action_target="npc_tabernero",
        )
        self.assertEqual(eff.target, "npc_tabernero")
        self.assertEqual(eff.timing, "active")
        self.assertEqual(eff.give_gold, 50)
        self.assertIn("llave_bronce", eff.give_items)
        self.assertEqual(eff.affinity_delta, 0.1)
        self.assertTrue(eff.force_action)
        self.assertEqual(eff.trigger_action_type, "TALK")

    def test_lore_block_creation_and_helpers(self):
        eff_active = LoreEffects(
            target="npc_tabernero",
            timing="active",
            directive="Directiva al activarse",
            give_items=["objeto_mision"]
        )
        eff_done = LoreEffects(
            target="npc_tabernero",
            timing="done",
            directive="Directiva al terminar",
            give_gold=100
        )

        block = LoreBlock(
            id="lb_mision_principal",
            title="Misión Principal",
            state=LoreBlockState.UNKNOWN,
            conditions=[
                EntityCondition(entity_type="place", entity_id="Plaza Mayor", sub_condition="current_location")
            ],
            effects=[eff_active, eff_done]
        )

        self.assertEqual(block.id, "lb_mision_principal")
        self.assertEqual(block.title, "Misión Principal")
        self.assertEqual(block.state, LoreBlockState.UNKNOWN)
        self.assertEqual(len(block.conditions), 1)
        self.assertEqual(len(block.effects), 2)

        # Helpers de conveniencia
        self.assertIsNotNone(block.on_active)
        self.assertEqual(block.on_active.directive, "Directiva al activarse")
        self.assertIsNotNone(block.on_done)
        self.assertEqual(block.on_done.give_gold, 100)
        self.assertEqual(block.directive, "Directiva al activarse")


if __name__ == "__main__":
    unittest.main()
