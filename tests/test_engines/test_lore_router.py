"""Pruebas unitarias para LoreRouter, accesibilidad HSM, condiciones y efectos."""

import unittest
import os
from domains import EntityCondition, LoreBlock, LoreEffects
from engines.embedding.mock_backend import MockEmbeddingBackend
from engines.game.engine import GameEngine
from engines.game.lore_router import LoreRouter


class TestLoreRouter(unittest.TestCase):
    """Verifica el enrutador de lore, evaluación de condiciones y mutaciones de efectos."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)
        self.ctrl = self.engine.game_state_controller
        self.router = LoreRouter(embedding_backend=MockEmbeddingBackend())

    def tearDown(self):
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_evaluate_place_condition(self):
        # Lugar actual es Plaza Mayor (p_00)
        cond_curr = EntityCondition(entity_type="place", entity_id="Plaza Mayor", sub_condition="current_location")
        self.assertTrue(self.router.evaluate_single_condition(cond_curr, self.ctrl))

        # Lugar no actual
        cond_other = EntityCondition(entity_type="place", entity_id="Taberna", sub_condition="current_location")
        self.assertFalse(self.router.evaluate_single_condition(cond_other, self.ctrl))

        # Negación: NO estar en Taberna
        cond_other_neg = EntityCondition(
            entity_type="place", entity_id="Taberna", sub_condition="current_location", is_negated=True
        )
        self.assertTrue(self.router.evaluate_single_condition(cond_other_neg, self.ctrl))

    def test_evaluate_npc_affinity_condition(self):
        npc = self.ctrl.world_state.npcs["npc_tabernero"]
        npc.affinity = 0.5

        cond_ok = EntityCondition(entity_type="npc", entity_id="npc_tabernero", sub_condition="affinity", value=0.4)
        self.assertTrue(self.router.evaluate_single_condition(cond_ok, self.ctrl))

        cond_fail = EntityCondition(entity_type="npc", entity_id="npc_tabernero", sub_condition="affinity", value=0.8)
        self.assertFalse(self.router.evaluate_single_condition(cond_fail, self.ctrl))

    def test_hsm_hierarchy_accessibility_rule(self):
        # Un bloque raíz sin padre siempre es accesible
        parent = LoreBlock(id="lb_parent", title="Padre", state="unknown")
        child = LoreBlock(id="lb_child", title="Hijo", parent_id="lb_parent", state="unknown")

        self.ctrl.world_state.lore_blocks["lb_parent"] = parent
        self.ctrl.world_state.lore_blocks["lb_child"] = child

        # Mientras el padre esté en unknown, el hijo no es accesible
        self.assertTrue(self.router.is_block_accessible(parent, self.ctrl))
        self.assertFalse(self.router.is_block_accessible(child, self.ctrl))

        # Al activar el padre, el hijo se vuelve accesible
        parent.state = "active"
        self.assertTrue(self.router.is_block_accessible(child, self.ctrl))

    def test_apply_lore_effects(self):
        initial_gold = self.ctrl.player.gold
        initial_inv = len(self.ctrl.player.inventory)
        npc_aff = self.ctrl.world_state.npcs["npc_tabernero"].affinity

        effects = LoreEffects(
            gold_delta=50,
            give_items=["objeto_recompensa"],
            affinity_delta=0.15,
            target="npc_tabernero",
        )

        self.router.apply_lore_effects(effects, self.ctrl, npc=self.ctrl.world_state.npcs["npc_tabernero"])

        self.assertEqual(self.ctrl.player.gold, initial_gold + 50)
        self.assertEqual(len(self.ctrl.player.inventory), initial_inv + 1)
        self.assertIn("objeto_recompensa", self.ctrl.player.inventory)
        self.assertGreater(self.ctrl.world_state.npcs["npc_tabernero"].affinity, npc_aff)

    def test_evaluate_npc_affinity_condition_when_affinity_disabled(self):
        self.ctrl.world_state.story_config.affinity = False
        npc = self.ctrl.world_state.npcs["npc_tabernero"]
        npc.affinity = 0.5

        # Con afinidad desactivada, la condición se considera satisfecha para evitar bloqueos
        cond_high = EntityCondition(entity_type="npc", entity_id="npc_tabernero", sub_condition="affinity", value=0.9)
        self.assertTrue(self.router.evaluate_single_condition(cond_high, self.ctrl))

    def test_apply_lore_effects_when_affinity_disabled(self):
        self.ctrl.world_state.story_config.affinity = False
        npc_aff = self.ctrl.world_state.npcs["npc_tabernero"].affinity

        effects = LoreEffects(
            gold_delta=10,
            affinity_delta=0.25,
            target="npc_tabernero",
        )

        self.router.apply_lore_effects(effects, self.ctrl, npc=self.ctrl.world_state.npcs["npc_tabernero"])
        # Oro sí muta, pero afinidad no cambia
        self.assertEqual(self.ctrl.world_state.npcs["npc_tabernero"].affinity, npc_aff)


if __name__ == "__main__":
    unittest.main()
