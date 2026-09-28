"""Pruebas unitarias para las acciones narrativas: MoveAction, LookAction y DialogueAction."""

import os
import shutil
import tempfile
import unittest
from domains.game_state import LoreBlockHierarchy
from domains.items import Item
from domains.npcs import NPC, NPCMotivations
from domains.player import Player
from domains.world import Connection, Location, Place, World
from engines.game.actions import DialogueAction, LookAction, MoveAction
from engines.game.state_controller import GameStateController
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.engine import TransformerEngine


class MockLLMAdapter(BaseLLMAdapter):
    """Adaptador mock para simular respuestas JSON estructuradas del LLM."""

    def __init__(self, canned_response: dict):
        self.canned_response = canned_response
        self.last_prompt = None

    def generate(self, prompt: str, profile_name: str = "narrator", response_schema=None, schema_name=None):
        self.last_prompt = prompt
        return self.canned_response


class TestNarrativeActions(unittest.TestCase):
    """Verifica la generación de contextos y narrativa de las acciones del juego."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        self.p1 = Place(
            id="p1",
            name="Plaza Mayor",
            description="La plaza central del pueblo.",
            connections={"p2": Connection(target="p2", distance=100, terrain_type="village")},
        )
        self.p2 = Place(
            id="p2",
            name="Taberna",
            description="Una taberna acogedora.",
            connections={"p1": Connection(target="p1", distance=100, terrain_type="village")},
        )

        self.loc = Location(id="loc1", name="Aldea", description="Una aldea", places=[self.p1, self.p2])
        self.world = World(id="w1", name="Mundo", description="Un mundo", locations=[self.loc])

        self.player = Player(
            id="player1",
            name="Héroe",
            description="El protagonista",
            gold=10,
            inventory=["item_key"],
            initial_location="p1",
        )

        self.npc = NPC(
            id="npc_tabernero",
            name="Tabernero",
            description="El dueño de la taberna.",
            initial_location="p1",
            motivations=NPCMotivations(likes=["cerveza"], dislikes=["alborotadores"]),
        )
        self.item = Item(id="item_key", name="Llave Antigua", description="Una llave oxidada.", initial_location="p1")

        self.hierarchy = LoreBlockHierarchy(active=[], done=[], unknown=[])

        self.ctrl = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=[self.npc],
            items=[self.item],
            loreblocks_hierarchy=self.hierarchy,
            adventure_path=self.temp_dir,
            elapsed_time_enabled=True,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_move_action_fallback_and_llm(self):
        """MoveAction genera contexto y narra tanto en fallback como con TransformerEngine."""
        action = MoveAction(
            origin_place=self.p1,
            destination_place=self.p2,
            path_taken=[],
            travel_time=2,
        )
        ctx = action.build_context(self.ctrl, "caminar hacia la taberna")
        self.assertEqual(ctx.origin_place.id, "p1")
        self.assertEqual(ctx.destination_place.id, "p2")
        self.assertEqual(ctx.estimated_travel_time, 2)

        # Fallback sin LLM
        msg_fb, extra_fb = action.generate_narrative(self.ctrl, "caminar hacia la taberna", transformer_engine=None)
        self.assertIn("Llegas a Taberna", msg_fb)
        self.assertIsNone(extra_fb)

        # Con LLM Mock
        mock_adapter = MockLLMAdapter({"msg": "Cruzas el umbral de madera crujiente y entras en la Taberna."})
        transformer = TransformerEngine(llm_adapter=mock_adapter)
        msg_llm, _ = action.generate_narrative(self.ctrl, "caminar hacia la taberna", transformer_engine=transformer)
        self.assertEqual(msg_llm, "Cruzas el umbral de madera crujiente y entras en la Taberna.")
        self.assertIn("Taberna", mock_adapter.last_prompt)

    def test_dialogue_action_fallback_and_llm_affinity(self):
        """DialogueAction genera contexto y procesa respuesta y afinidad de LLM."""
        action = DialogueAction(target_npc="npc_tabernero")
        ctx = action.build_context(self.ctrl, "Hola tabernero, ¿tienes cerveza?")
        self.assertEqual(ctx.npc.name, "Tabernero")
        self.assertEqual(ctx.player_input, "Hola tabernero, ¿tienes cerveza?")

        # Fallback sin LLM
        msg_fb, _ = action.generate_narrative(self.ctrl, "Hola tabernero", transformer_engine=None)
        self.assertIn("He escuchado lo que dices", msg_fb)

        # Con LLM Mock con afinidad
        mock_adapter = MockLLMAdapter({"msg": "¡Por supuesto viajero! Toma una bien fría.", "affinity": 0.9})
        transformer = TransformerEngine(llm_adapter=mock_adapter)
        msg_llm, affinity = action.generate_narrative(self.ctrl, "cerveza por favor", transformer_engine=transformer)
        self.assertEqual(msg_llm, "¡Por supuesto viajero! Toma una bien fría.")
        self.assertEqual(affinity, 0.9)

    def test_look_action_fallback_and_llm(self):
        """LookAction resuelve entidad objetivo y narra con o sin LLM."""
        # Mirar entidad Item
        action = LookAction(target="item_key")
        ctx = action.build_context(self.ctrl, "examinar llave")
        self.assertIsNotNone(ctx.entity)
        self.assertEqual(ctx.entity.id, "item_key")

        msg_fb, _ = action.generate_narrative(self.ctrl, "examinar llave", transformer_engine=None)
        self.assertIn("Examinas Llave Antigua", msg_fb)

        # Con LLM Mock
        mock_adapter = MockLLMAdapter({"msg": "La llave muestra runas arcanas grabadas en el metal."})
        transformer = TransformerEngine(llm_adapter=mock_adapter)
        msg_llm, _ = action.generate_narrative(self.ctrl, "examinar llave", transformer_engine=transformer)
        self.assertEqual(msg_llm, "La llave muestra runas arcanas grabadas en el metal.")


if __name__ == "__main__":
    unittest.main()
