"""Pruebas unitarias para las acciones del motor: MoveAction, LookAction y DialogueAction."""

import unittest
import os
from domains import ExplainLookResponse, MoveNarratorResponse
from engines.game.engine import GameEngine
from engines.game.actions import MoveAction, LookAction, DialogueAction
from engines.game.actions.dialogue_action import DialogueNarratorResponse


class TestActions(unittest.TestCase):
    """Verifica la ejecución determinista y mutación de estado de las acciones."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)
        self.ctrl = self.engine.game_state_controller

    def tearDown(self):
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_move_action_lifecycle(self):
        self.assertEqual(self.ctrl.place.id, "p_00")

        # Mover a Calle Pobre (p_01)
        move_action = MoveAction("p_01")
        response = MoveNarratorResponse(msg="Caminas hacia la Calle Pobre.")
        res = move_action.execute(self.ctrl, "ir a calle pobre", response)

        self.assertTrue(res.success)
        self.assertEqual(self.ctrl.place.id, "p_01")
        self.assertEqual(self.ctrl.data.prev_place.id, "p_00")
        self.assertEqual(self.ctrl.data.current_place.id, "p_01")

    def test_look_action_npc_and_place(self):
        # Mirar al tabernero
        look_npc = LookAction("npc_tabernero")
        ctx = look_npc.build_context(self.ctrl, "mirar al tabernero")
        self.assertEqual(ctx.entity.id, "npc_tabernero")

        res_npc = look_npc.execute(self.ctrl, "mirar al tabernero", ExplainLookResponse(msg="Lleva un delantal manchado."))
        self.assertTrue(res_npc.success)
        self.assertIn("Lleva un delantal manchado.", self.ctrl.world_state.npcs["npc_tabernero"].description)

        # Mirar la taberna (p_03)
        look_place = LookAction("p_03")
        res_place = look_place.execute(self.ctrl, "mirar taberna", ExplainLookResponse(msg="Se escucha música de laúd."))
        self.assertTrue(res_place.success)
        self.assertIn("Se escucha música de laúd.", self.ctrl.world_state.places_by_id["p_03"].description)

    def test_dialogue_action_affinity_and_history(self):
        init_aff = self.ctrl.world_state.npcs["npc_tabernero"].affinity
        dialogue = DialogueAction("npc_tabernero")
        resp = DialogueNarratorResponse(msg="¡Bienvenido a mi taberna!", affinity="GOOD")

        res = dialogue.execute(self.ctrl, "Saludos buen hombre", resp)
        self.assertTrue(res.success)
        self.assertEqual(res.message, "¡Bienvenido a mi taberna!")

        new_aff = self.ctrl.world_state.npcs["npc_tabernero"].affinity
        self.assertGreaterEqual(new_aff, init_aff)


if __name__ == "__main__":
    unittest.main()
