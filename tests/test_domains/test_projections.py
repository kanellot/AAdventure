"""Pruebas unitarias para las Proyecciones y DTOs de Cliente (domains.projections)."""

import unittest

from domains.game_state import NotebookEntry
from domains.projections.debug import (
    ConnectionProjection,
    GameSnapshotProjection,
    PlaceDetailProjection,
    PlayerSummaryProjection,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnDebugProjection,
)
from domains.projections.game import (
    ActionCommandProjection,
    InventoryItemDTO,
    InventoryProjection,
    MapItemDTO,
    MapLocationDTO,
    MapNPCDTO,
    MapPlaceDTO,
    MoveOptionProjection,
    NotebookProjection,
    PlaceProjection,
    TurnOutput,
    TurnResultProjection,
    UIStateProjection,
    WorldMapProjection,
)


class TestProjections(unittest.TestCase):
    """Pruebas de modelos DTO y proyecciones de estado estándar."""

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
            terrain="village",
        )
        self.assertEqual(move.direction, "norte")
        self.assertEqual(move.target, "Calle Pobre")
        self.assertEqual(move.distance, 150)
        self.assertEqual(move.terrain, "village")

    def test_action_command(self):
        cmd = ActionCommandProjection(action="MOVE", target="Calle Pobre")
        self.assertEqual(cmd.action, "MOVE")
        self.assertEqual(cmd.target, "Calle Pobre")

    def test_turn_output_and_map_dtos(self):
        output = TurnOutput(
            author="Dungeon Master",
            type="msg",
            msg="Caminas hacia la plaza.",
            player_state="EXPLORE",
        )
        self.assertEqual(output.author, "Dungeon Master")
        self.assertEqual(output.type, "msg")

        item = MapItemDTO(id="item_sword", name="Espada", visible=True)
        npc = MapNPCDTO(id="npc_guard", name="Guardia", status="visible")
        place = MapPlaceDTO(
            id="p_01",
            name="Plaza",
            status="visited",
            entities=[item, npc],
        )
        location = MapLocationDTO(id="loc_01", name="Pueblo", places=[place])
        world_map = WorldMapProjection(locations=[location])

        self.assertEqual(len(world_map.locations), 1)
        self.assertEqual(world_map.locations[0].places[0].status, "visited")
        self.assertEqual(len(world_map.locations[0].places[0].entities), 2)

    def test_inventory_and_notebook_dtos(self):
        inv = InventoryProjection(
            items=[InventoryItemDTO(id="it_1", name="Poción", description="Cura 10 HP")],
            gold=75,
        )
        self.assertEqual(inv.gold, 75)
        self.assertEqual(len(inv.items), 1)

        notebook = NotebookProjection(
            quests=[NotebookEntry(id="q_1", name="Salvar el pueblo", status="active")]
        )
        self.assertEqual(len(notebook.quests), 1)
        self.assertEqual(notebook.quests[0].status, "active")

    def test_turn_result_projection(self):
        """Verifica la proyección consolidada completa entregada a la UI."""
        res = TurnResultProjection(
            output=TurnOutput(
                author="SYSTEM",
                type="msg",
                msg="Llegas a la Taberna del Jabalí.",
                player_state="EXPLORE",
            ),
            map=WorldMapProjection(
                locations=[
                    MapLocationDTO(
                        id="loc_1",
                        name="Valle",
                        places=[MapPlaceDTO(id="p_1", name="Taberna", status="visited")],
                    )
                ]
            ),
            inventory=InventoryProjection(items=[], gold=20),
            notebook=NotebookProjection(quests=[]),
        )
        self.assertEqual(res.output.author, "SYSTEM")
        self.assertEqual(res.output.msg, "Llegas a la Taberna del Jabalí.")
        self.assertEqual(res.inventory.gold, 20)
        self.assertIsNone(res.debug)

    def test_turn_result_projection_with_debug_dto(self):
        """Los depuradores consumen el DTO TurnDebugProjection opcional."""
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
                        is_matched=True,
                    )
                ],
            ),
        )
        res = TurnResultProjection(
            output=TurnOutput(author="Tabernero", type="msg", msg="Bienvenido.", player_state="TALK"),
            map=WorldMapProjection(),
            inventory=InventoryProjection(),
            notebook=NotebookProjection(),
            debug=debug_dto,
        )
        self.assertIsNotNone(res.debug)
        self.assertEqual(res.debug.prompt, "Prompt de prueba para LLM")
        self.assertEqual(res.debug.raw_response, '{"msg": "Hola viajero"}')
        self.assertIsNotNone(res.debug.rag_evaluation)
        self.assertEqual(len(res.debug.rag_evaluation.antennas), 1)

    def test_ui_state_projection(self):
        ui = UIStateProjection(
            player_name="Héroe",
            gold=100,
            current_location="Plaza",
            formatted_time="Día 1, 10:00",
            game_state="EXPLORE",
        )
        self.assertEqual(ui.player_name, "Héroe")
        self.assertEqual(ui.gold, 100)

    def test_debug_projections(self):
        player_summary = PlayerSummaryProjection(id="p_01", name="Jugador", gold=50)
        self.assertEqual(player_summary.name, "Jugador")
        self.assertEqual(player_summary.gold, 50)

        conn = ConnectionProjection(target="B", direction="norte", distance=10, terrain_type="road")
        self.assertEqual(conn.distance, 10)

        place_detail = PlaceDetailProjection(id="A", name="Lugar A", connections=[conn])
        self.assertEqual(len(place_detail.connections), 1)

        snap = GameSnapshotProjection(
            player=player_summary,
            current_place="A",
        )
        self.assertEqual(snap.player.name, "Jugador")
        self.assertEqual(snap.current_place, "A")


if __name__ == "__main__":
    unittest.main()
