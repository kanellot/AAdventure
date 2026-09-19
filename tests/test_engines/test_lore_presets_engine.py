"""Pruebas unitarias del motor para presets de LoreBlock, condiciones avanzadas, bypass de LLM y popups."""

import os
import unittest
from domains import EntityCondition, LoreBlock, LoreEffects
from domains.projections import ActionCommandProjection
from engines.embedding.mock_backend import MockEmbeddingBackend
from engines.game.engine import GameEngine
from engines.game.lore_router import LoreRouter
from engines.transformer.mock_adapter import MockLLMAdapter
from engines.transformer.engine import TransformerEngine


class TestLorePresetsEngine(unittest.TestCase):
    """Verifica el comportamiento en runtime de los presets, bypass de LLM y condiciones de lore."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(world_json_path=self.aad_path)
        self.ctrl = self.engine.game_state_controller
        self.router = LoreRouter(embedding_backend=MockEmbeddingBackend())
        self.dm = TransformerEngine(MockLLMAdapter())

    def tearDown(self):
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

    def test_all_children_done_condition(self):
        """all_children_done evalúa True solo si TODOS los hijos del bloque padre están en 'done'."""
        parent = LoreBlock(id="quest_01", name="Misión Principal", preset="quest", state="active")
        child1 = LoreBlock(id="task_01", name="Tarea 1", preset="task", parent_id="quest_01", state="done")
        child2 = LoreBlock(id="task_02", name="Tarea 2", preset="task", parent_id="quest_01", state="active")

        self.ctrl.world_state.lore_blocks["quest_01"] = parent
        self.ctrl.world_state.lore_blocks["task_01"] = child1
        self.ctrl.world_state.lore_blocks["task_02"] = child2

        cond = EntityCondition(
            entity_type="loreblock",
            entity_id="quest_01",
            sub_condition="all_children_done",
        )

        # Con task_02 aún en active, all_children_done debe ser False
        self.assertFalse(self.router.evaluate_single_condition(cond, self.ctrl, evaluating_block=parent))

        # Al completar task_02, all_children_done debe ser True
        child2.state = "done"
        self.assertTrue(self.router.evaluate_single_condition(cond, self.ctrl, evaluating_block=parent))

    def test_affinity_range_condition(self):
        """affinity_range evalúa si la afinidad del NPC cae en el intervalo [min, max]."""
        npc = self.ctrl.world_state.npcs["npc_tabernero"]
        npc.affinity = 0.65

        cond_match = EntityCondition(
            entity_type="npc",
            entity_id="npc_tabernero",
            sub_condition="affinity_range",
            value=[0.5, 0.8],
        )
        self.assertTrue(self.router.evaluate_single_condition(cond_match, self.ctrl, npc=npc))

        cond_mismatch = EntityCondition(
            entity_type="npc",
            entity_id="npc_tabernero",
            sub_condition="affinity_range",
            value=[0.7, 1.0],
        )
        self.assertFalse(self.router.evaluate_single_condition(cond_mismatch, self.ctrl, npc=npc))

    def test_time_range_condition(self):
        """time_range evalúa si elapsed_time se encuentra en el rango horario establecido."""
        self.ctrl.data.state.elapsed_time = 150

        cond_ok = EntityCondition(
            entity_type="time",
            entity_id="",
            sub_condition="time_range",
            value=[100, 200],
        )
        self.assertTrue(self.router.evaluate_single_condition(cond_ok, self.ctrl))

        cond_out = EntityCondition(
            entity_type="time",
            entity_id="",
            sub_condition="time_range",
            value=[250, 400],
        )
        self.assertFalse(self.router.evaluate_single_condition(cond_out, self.ctrl))

    def test_dialogue_bypass_llm_returns_verbatim_text(self):
        """Cuando un bloque tiene bypass_llm = True, el motor devuelve el texto exacto sin llamar al LLM."""
        direct_quote = "El tabernero te mira fijamente y dice: '¡Basta de preguntas, coge esta llave y vete!'"
        direct_block = LoreBlock(
            id="diag_direct_01",
            name="Respuesta Directa Tabernero",
            preset="event_diag",
            state="active",
            conditions=[],
            effects=[
                LoreEffects(
                    timing="active",
                    target="npc_tabernero",
                    execution_mode="hook",
                    bypass_llm=True,
                    directive=direct_quote,
                )
            ],
        )
        self.ctrl.world_state.lore_blocks["diag_direct_01"] = direct_block

        res = self.engine.execute_turn(
            ActionCommandProjection(action="TALK", target="npc_tabernero"),
            dm=self.dm,
        )

        self.assertIn(direct_quote, res.msg)

    def test_event_popup_populates_popup_fields(self):
        """Un bloque con preset 'event_popup' puebla popup_message en el resultado del turno."""
        popup_text = "¡Un temblor repentino sacude la plaza y caen escombros de la muralla!"
        popup_block = LoreBlock(
            id="pop_temblor",
            name="Terremoto",
            preset="event_popup",
            state="active",
            conditions=[],
            effects=[
                LoreEffects(
                    timing="active",
                    target="Plaza Mayor",
                    execution_mode="push",
                    bypass_llm=True,
                    directive=popup_text,
                )
            ],
        )
        self.ctrl.world_state.lore_blocks["pop_temblor"] = popup_block

        res = self.engine.execute_turn(
            ActionCommandProjection(action="LOOK", target="Plaza Mayor"),
            dm=self.dm,
        )

        self.assertIsNotNone(res.popup_message)
        self.assertIn(popup_text, res.popup_message)


if __name__ == "__main__":
    unittest.main()
