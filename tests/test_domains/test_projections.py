"""Pruebas unitarias para las Proyecciones y DTOs de Cliente (domains.projections)."""

import unittest
from domains.projections import (
    PlaceProjection,
    MoveOptionProjection,
    AvailableActionsProjection,
    UIStateProjection,
    TurnResultProjection,
    LoreConditionDetailProjection,
    LoreBlockDetailProjection,
)


class TestProjections(unittest.TestCase):
    """Pruebas de modelos DTO y proyecciones de estado."""

    def test_place_projection(self):
        proj = PlaceProjection(id="p_01", name="Plaza Mayor", status="visited")
        self.assertEqual(proj.id, "p_01")
        self.assertEqual(proj.name, "Plaza Mayor")
        self.assertEqual(proj.status, "visited")

    def test_move_option_projection(self):
        move = MoveOptionProjection(
            direction="norte",
            target="Calle Pobre",
            distance=150,
            terrain="village"
        )
        self.assertEqual(move.direction, "norte")
        self.assertEqual(move.target, "Calle Pobre")
        self.assertEqual(move.distance, 150)
        self.assertEqual(move.terrain, "village")

    def test_turn_result_projection(self):
        res = TurnResultProjection(
            author="SYSTEM",
            msg="Llegas a la Taberna del Jabalí.",
            info_msg="Tiempo transcurrido: 2 min."
        )
        self.assertEqual(res.author, "SYSTEM")
        self.assertEqual(res.msg, "Llegas a la Taberna del Jabalí.")
        self.assertEqual(res.info_msg, "Tiempo transcurrido: 2 min.")
        self.assertIsNone(res.debug_prompt)

    def test_ui_state_projection(self):
        ui = UIStateProjection(
            player_name="Héroe",
            gold=100,
            current_location="Plaza",
            formatted_time="Día 1, 10:00",
            game_state="EXPLORE",
            can_send_message=False,
            allowed_actions=["MOVE", "LOOK", "TALK"],
        )
        self.assertEqual(ui.player_name, "Héroe")
        self.assertEqual(ui.gold, 100)
        self.assertFalse(ui.can_send_message)
        self.assertEqual(ui.allowed_actions, ["MOVE", "LOOK", "TALK"])


    def test_lore_block_detail_projection(self):
        cond_detail = LoreConditionDetailProjection(
            entity_type="npc",
            entity_id="npc_tabernero",
            sub_condition="affinity",
            value=0.5,
            is_met=True
        )
        block_proj = LoreBlockDetailProjection(
            id="lb_01",
            name="Misión 1",
            title="Buscar la llave",
            state="active",
            conditions=[cond_detail]
        )
        self.assertEqual(block_proj.id, "lb_01")
        self.assertEqual(block_proj.state, "active")
        self.assertEqual(len(block_proj.conditions), 1)
        self.assertTrue(block_proj.conditions[0].is_met)


if __name__ == "__main__":
    unittest.main()
