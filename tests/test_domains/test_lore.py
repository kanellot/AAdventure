"""Pruebas unitarias para modelos de Lore y Condiciones HSM (domains.lore)."""

import unittest

from domains.lore import EntityCondition, ConditionGroup, LoreEffects, LoreBlock, LoreBlockState


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
            directive="El tabernero te mira con recelo.",
            gold_delta=50,
            give_items=["llave_bronce"],
            affinity_delta=0.1,
            action="push",
            elapsed_time="01:15",
            unlock_places=["p_bodega"],
            unlock_npcs=["npc_camarera"],
            unlock_items=["obj_barril"],
            block_places=["p_puerta_trasera"],
            unblock_places=["p_entrada_principal"],
        )
        self.assertEqual(eff.target, "npc_tabernero")
        self.assertEqual(eff.gold_delta, 50)
        self.assertIn("llave_bronce", eff.give_items)
        self.assertEqual(eff.affinity_delta, 0.1)
        self.assertEqual(eff.action, "push")
        self.assertEqual(eff.elapsed_time, "01:15")
        self.assertEqual(eff.unlock_places, ["p_bodega"])
        self.assertEqual(eff.unlock_npcs, ["npc_camarera"])
        self.assertEqual(eff.unlock_items, ["obj_barril"])
        self.assertEqual(eff.block_places, ["p_puerta_trasera"])
        self.assertEqual(eff.unblock_places, ["p_entrada_principal"])

    def test_lore_block_creation_and_structure(self):
        eff_active = LoreEffects(
            target="npc_tabernero",
            directive="Directiva al activarse",
            give_items=["objeto_mision"],
            action="hook",
            elapsed_time="00:30",
        )

        cond_act = EntityCondition(entity_type="place", entity_id="Plaza Mayor", sub_condition="current_location")
        cond_done = EntityCondition(entity_type="item", entity_id="objeto_mision", sub_condition="have")

        block = LoreBlock(
            id="lb_mision_principal",
            name="Misión Principal",
            title="Misión Principal",
            type="Quest",
            state=LoreBlockState.UNKNOWN,
            active_conditions=[
                ConditionGroup(conditions=[cond_act], rag_enabled=True, trigger_phrases=["¿dónde voy?"])
            ],
            done_conditions=[
                ConditionGroup(conditions=[cond_done], rag_enabled=False, trigger_phrases=[])
            ],
            active_effects=[eff_active],
            done_effects=[],
        )

        self.assertEqual(block.id, "lb_mision_principal")
        self.assertEqual(block.title, "Misión Principal")
        self.assertEqual(block.type, "Quest")
        self.assertEqual(block.state, LoreBlockState.UNKNOWN)
        self.assertEqual(len(block.active_conditions), 1)
        self.assertEqual(len(block.active_conditions[0].conditions), 1)
        self.assertTrue(block.active_conditions[0].rag_enabled)
        self.assertEqual(len(block.done_conditions), 1)
        self.assertEqual(len(block.done_conditions[0].conditions), 1)
        self.assertFalse(block.done_conditions[0].rag_enabled)
        self.assertEqual(len(block.active_effects), 1)
        self.assertEqual(block.active_effects[0].elapsed_time, "00:30")
        self.assertEqual(block.active_effects[0].action, "hook")
        self.assertEqual(len(block.done_effects), 0)


if __name__ == "__main__":
    unittest.main()
