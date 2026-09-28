"""Pruebas unitarias para el subsistema desacoplado de Lore (HSM, Condiciones y Efectos)."""

import unittest
from domains.player import Player
from domains.world import World, Location, Place
from domains.npcs import NPC
from domains.items import Item
from domains.game_state import LoreBlockHierarchy
from engines.game.state_controller import GameStateController
from engines.game.lore import (
    LoreConditionEvaluator,
    LoreEffectApplier,
    LoreStateMachine,
)


class TestLoreSubsystem(unittest.TestCase):
    """Verifica el comportamiento aislado del evaluador de condiciones, aplicador de efectos y HSM."""

    def setUp(self):
        p1 = Place(id="p_01", name="Plaza", description="Una plaza.")
        p2 = Place(id="p_02", name="Bosque", description="Un bosque.")
        loc = Location(id="l_01", name="Mundo", description="Loc", places=[p1, p2])
        self.world = World(id="w_01", name="Test", description="W", locations=[loc])
        self.player = Player(id="p", name="Hero", description="D", initial_location="p_01", gold=10)
        self.npc = NPC(id="npc_bardo", name="Bardo", description="D", initial_location="p_01", affinity=0.6)
        self.item = Item(id="item_llave", name="Llave", description="D", initial_location="p_01")
        self.ctrl = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=[self.npc],
            items=[self.item],
            fog_war_enabled=True,
        )

    def test_condition_evaluator_place_and_gold(self):
        # Place current location
        cond_loc = {"entity_type": "place", "entity_id": "p_01", "sub_condition": "current_location"}
        self.assertTrue(LoreConditionEvaluator.is_single_condition_met(cond_loc, self.ctrl))

        cond_loc_bad = {"entity_type": "place", "entity_id": "p_02", "sub_condition": "current_location"}
        self.assertFalse(LoreConditionEvaluator.is_single_condition_met(cond_loc_bad, self.ctrl))

        # Gold
        cond_gold = {"entity_type": "gold", "entity_id": "gold", "sub_condition": "have", "value": 5}
        self.assertTrue(LoreConditionEvaluator.is_single_condition_met(cond_gold, self.ctrl))

        cond_gold_bad = {"entity_type": "gold", "entity_id": "gold", "sub_condition": "have", "value": 20}
        self.assertFalse(LoreConditionEvaluator.is_single_condition_met(cond_gold_bad, self.ctrl))

    def test_condition_evaluator_npc_affinity_and_item(self):
        # NPC affinity
        cond_aff = {"entity_type": "npc", "entity_id": "npc_bardo", "sub_condition": "affinity", "value": 0.5}
        self.assertTrue(LoreConditionEvaluator.is_single_condition_met(cond_aff, self.ctrl))

        # Item visible in current location
        cond_item_vis = {"entity_type": "item", "entity_id": "item_llave", "sub_condition": "visible"}
        self.assertTrue(LoreConditionEvaluator.is_single_condition_met(cond_item_vis, self.ctrl))

    def test_effect_applier_mutations(self):
        autonomous = []
        effects = [
            {"gold_delta": 25, "affinity_delta": 0.2, "target": "npc_bardo", "give_items": ["item_llave"]},
        ]
        LoreEffectApplier.apply_effects(effects, self.ctrl, autonomous)

        self.assertEqual(self.ctrl.game_state.gold, 35)
        self.assertAlmostEqual(self.ctrl.get_npc_affinity("npc_bardo"), 0.8)
        self.assertIn("item_llave", self.ctrl.game_state.inventory.items)

    def test_state_machine_popup_direct_done(self):
        popup_blk = {
            "id": "pop_welcome",
            "name": "Bienvenido",
            "type": "popup",
            "description": "Texto modal de bienvenida",
            "active_conditions": [],
            "done_conditions": [],
            "effects": [],
        }
        self.ctrl.game_state.loreblocks.unknown.append(popup_blk)

        res = LoreStateMachine.execute_cycle(self.ctrl)
        self.assertEqual(res.popup_title, "Bienvenido")
        self.assertEqual(res.popup_message, "Texto modal de bienvenida")
        self.assertIn(popup_blk, self.ctrl.game_state.loreblocks.done)
        self.assertNotIn(popup_blk, self.ctrl.game_state.loreblocks.unknown)


if __name__ == "__main__":
    unittest.main()
