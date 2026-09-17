"""Pruebas unitarias para las Proyecciones y DTOs de Cliente (domains.projections)."""

import unittest
from domains.projections.game import (
    ActionCommand,
    ActionCommandProjection,
    AvailableActionsProjection,
    LocationHierarchyProjection,
    MoveOptionProjection,
    PlaceProjection,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
)
from domains.projections.debug import (
    ConnectionProjection,
    GameSnapshotProjection,
    GameStateProjection,
    LoreBlockDetailProjection,
    LoreConditionDetailProjection,
    LoreGraphProjection,
    PlaceDetailProjection,
    PlayerSummaryProjection,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnDebugProjection,
)


class TestProjections(unittest.TestCase):
    """Pruebas de modelos DTO y proyecciones de estado (Game UI vs Debug)."""

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

    def test_action_command_projection(self):
        cmd = ActionCommandProjection(action="MOVE", target="Calle Pobre")
        self.assertEqual(cmd.action, "MOVE")
        self.assertEqual(cmd.target, "Calle Pobre")
        self.assertIs(ActionCommand, ActionCommandProjection)

    def test_turn_result_projection_clean_game_ui(self):
        """La UI de juego solo necesita consumir author, msg e info_msg."""
        res = TurnResultProjection(
            author="SYSTEM",
            msg="Llegas a la Taberna del Jabalí.",
            info_msg="Tiempo transcurrido: 2 min."
        )
        self.assertEqual(res.author, "SYSTEM")
        self.assertEqual(res.msg, "Llegas a la Taberna del Jabalí.")
        self.assertEqual(res.info_msg, "Tiempo transcurrido: 2 min.")
        self.assertIsNone(res.debug)
        self.assertIsNone(res.debug_prompt)

    def test_turn_result_projection_with_debug_dto(self):
        """Los depuradores consumen el DTO TurnDebugProjection."""
        debug_dto = TurnDebugProjection(
            prompt="Prompt de prueba para LLM",
            raw_response='{"msg": "Hola viajero"}',
            structured_response='{"msg": "Hola viajero"}',
            engine_result="Turno completado exitosamente",
            rag_evaluation=RagEvaluationProjection(
                player_input="hola",
                threshold=0.65,
                antennas=[
                    RagAntennaScoreProjection(
                        antenna="hola",
                        lore_id="lb_01",
                        lore_title="Misión 1",
                        score=0.92,
                        is_matched=True
                    )
                ]
            )
        )
        res = TurnResultProjection(
            author="Tabernero",
            msg="Bienvenido a mi taberna.",
            debug=debug_dto
        )
        self.assertIsNotNone(res.debug)
        self.assertEqual(res.debug.prompt, "Prompt de prueba para LLM")
        # Verificar propiedades de conveniencia
        self.assertEqual(res.debug_prompt, "Prompt de prueba para LLM")
        self.assertEqual(res.debug_raw_response, '{"msg": "Hola viajero"}')
        self.assertIsNotNone(res.rag_evaluation)
        self.assertEqual(len(res.rag_evaluation.antennas), 1)

    def test_turn_result_projection_legacy_kwargs_compatibility(self):
        """Comprueba que pasar kwargs de debug legacy sigue funcionando transparentemente."""
        res = TurnResultProjection(
            author="SYSTEM",
            msg="Mensaje",
            debug_prompt="Prompt heredado"
        )
        self.assertIsNotNone(res.debug)
        self.assertEqual(res.debug.prompt, "Prompt heredado")
        self.assertEqual(res.debug_prompt, "Prompt heredado")

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

    def test_game_state_projection(self):
        player_summary = PlayerSummaryProjection(id="p_01", name="Jugador", gold=50)
        place_detail = PlaceDetailProjection(
            id="plaza",
            name="Plaza Mayor",
            connections=[ConnectionProjection(direction="norte", target="calle", distance=100)]
        )
        gs = GameStateProjection(
            player=player_summary,
            current_place="plaza",
            current_place_detail=place_detail,
            discovered_places=["plaza", "calle"],
            active_lore_blocks=["lb_01"],
            done_lore_blocks=[]
        )
        self.assertEqual(gs.player.name, "Jugador")
        self.assertEqual(gs.current_place_detail.connections[0].direction, "norte")
        self.assertEqual(gs.active_lore_blocks, ["lb_01"])


if __name__ == "__main__":
    unittest.main()
