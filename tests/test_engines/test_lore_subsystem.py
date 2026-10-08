"""Pruebas unitarias para el subsistema desacoplado de Lore (HSM, Condiciones y Efectos)."""

import unittest
from unittest.mock import MagicMock

from domains.items import Item
from domains.npcs import NPC
from domains.player import Player
from domains.world import World, Location, Place
from engines.game.lore import (
    LoreConditionEvaluator,
    LoreEffectApplier,
    LoreStateMachine,
)
from engines.game.state_controller import GameStateController


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

    def test_doble_effect_active_and_done_phases(self):
        """Verifica que active_effects se ejecuten al pasar a active y done_effects al pasar a done."""
        blk = {
            "id": "blk_de",
            "name": "Doble Efecto Test",
            "type": "Event",
            "state": "unknown",
            "active_conditions": [],
            "done_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {"entity_type": "place", "entity_id": "p_01", "sub_condition": "current_location"}
                    ],
                }
            ],
            "active_effects": [
                {"gold_delta": 5, "affinity_delta": 0.0, "target": None, "give_items": []}
            ],
            "done_effects": [
                {"gold_delta": 10, "affinity_delta": 0.0, "target": None, "give_items": ["item_llave"]}
            ],
        }
        self.ctrl.game_state.loreblocks.unknown.append(blk)

        # Ciclo 1: pasa a active (ejecuta active_effects: +5 oro) y luego a done (ejecuta done_effects: +10 oro, item)
        LoreStateMachine.execute_cycle(self.ctrl)

        # 10 inicial + 5 (active) + 10 (done) = 25
        self.assertEqual(self.ctrl.game_state.gold, 25)
        self.assertIn("item_llave", self.ctrl.game_state.inventory.items)
        self.assertIn(blk, self.ctrl.game_state.loreblocks.done)

    def test_info_preset_cascading_completion_on_parent_done(self):
        """Verifica que un bloque Info activo se complete automáticamente al pasar su padre a done."""
        parent_quest = {
            "id": "q_parent",
            "name": "Misión Padre",
            "type": "Quest",
            "state": "active",
            "active_conditions": [],
            "done_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {"entity_type": "place", "entity_id": "p_01", "sub_condition": "current_location"}
                    ],
                }
            ],
            "active_effects": [],
            "done_effects": [],
        }
        info_child = {
            "id": "info_pista",
            "name": "Pista Info",
            "type": "Info",
            "parent_id": "q_parent",
            "state": "active",
            "active_conditions": [],
            "done_conditions": [],
            "active_effects": [{"action": "hook", "directive": "Pista de contexto"}],
            "done_effects": [],
        }
        self.ctrl.game_state.loreblocks.active.append(parent_quest)
        self.ctrl.game_state.loreblocks.active.append(info_child)

        LoreStateMachine.execute_cycle(self.ctrl)

        done_ids = {b.get("id") for b in self.ctrl.game_state.loreblocks.done}
        self.assertIn("q_parent", done_ids)
        self.assertIn("info_pista", done_ids, "El bloque Info debe haber completado en cascada al completarse su padre.")

    def test_all_children_done_excludes_info_and_popup(self):
        """Verifica que all_children_done evalúe a True ignorando bloques Info y popup que no tienen done_conditions."""
        parent_chapter = {
            "id": "c_capitulo",
            "name": "Capítulo",
            "type": "Chapter",
            "state": "active",
        }
        child_quest = {
            "id": "q_hija",
            "name": "Quest Hija",
            "type": "Quest",
            "parent_id": "c_capitulo",
            "state": "done",
        }
        child_info = {
            "id": "info_hija",
            "name": "Info Hija",
            "type": "Info",
            "parent_id": "c_capitulo",
            "state": "active",  # Sigue active hasta que el padre complete
        }
        self.ctrl.game_state.loreblocks.active.append(parent_chapter)
        self.ctrl.game_state.loreblocks.done.append(child_quest)
        self.ctrl.game_state.loreblocks.active.append(child_info)

        cond = {"entity_type": "loreblock", "entity_id": "c_capitulo", "sub_condition": "all_children_done"}
        self.assertTrue(LoreConditionEvaluator.is_single_condition_met(cond, self.ctrl))

    def test_push_action_does_not_move_player_and_resolves_to_look(self):
        """Verifica que push a un lugar genera LOOK (no MOVE) y no desplaza al jugador."""
        autonomous: list = []
        effects = [
            {"action": "push", "target": "p_02", "directive": "Una torre se alza a lo lejos"},
        ]
        LoreEffectApplier.apply_effects(effects, self.ctrl, autonomous)

        self.assertEqual(len(autonomous), 1)
        push = autonomous[0]
        self.assertEqual(push.action, "LOOK")
        self.assertEqual(push.target, "p_02")
        self.assertEqual(push.directive, "Una torre se alza a lo lejos")
        # El jugador permanece en su posición original p_01
        self.assertEqual(self.ctrl.game_state.current_location, "p_01")

    def test_push_action_targets_npc_as_talk(self):
        """Verifica que push a un NPC genera una acción TALK."""
        autonomous: list = []
        effects = [
            {"action": "push", "target": "npc_bardo", "directive": "¡Saludos viajero!"},
        ]
        LoreEffectApplier.apply_effects(effects, self.ctrl, autonomous)

        self.assertEqual(len(autonomous), 1)
        push = autonomous[0]
        self.assertEqual(push.action, "TALK")
        self.assertEqual(push.target, "npc_bardo")
        self.assertEqual(push.directive, "¡Saludos viajero!")

    def test_multiple_popups_collected_in_cycle(self):
        """Verifica que múltiples popups disparados en un turno se recolectan individualmente."""
        pop1 = {"id": "pop1", "type": "popup", "state": "unknown", "title": "Aviso 1", "description": "Msg 1"}
        pop2 = {"id": "pop2", "type": "popup", "state": "unknown", "title": "Aviso 2", "description": "Msg 2"}
        pop3 = {"id": "pop3", "type": "popup", "state": "unknown", "title": "Aviso 3", "description": "Msg 3"}
        self.ctrl.game_state.loreblocks.unknown.extend([pop1, pop2, pop3])

        res = LoreStateMachine.execute_cycle(self.ctrl)
        self.assertEqual(len(res.popups), 3)
        self.assertEqual(res.popups[0], ("Aviso 1", "Msg 1"))
        self.assertEqual(res.popups[1], ("Aviso 2", "Msg 2"))
        self.assertEqual(res.popups[2], ("Aviso 3", "Msg 3"))

    def test_rag_conditions_short_circuit_when_normal_conditions_fail(self):
        """Verifica que si las condiciones normales fallan, RAG no calcula embeddings."""
        mock_embedding = MagicMock()
        group = {
            "rag_enabled": True,
            "trigger_phrases": ["hola"],
            "conditions": [
                {"entity_type": "place", "entity_id": "p_02", "sub_condition": "current_location"}  # Falso (está en p_01)
            ],
        }
        met = LoreConditionEvaluator.are_condition_groups_met(
            [group],
            self.ctrl,
            eval_query="hola",
            embedding_engine=mock_embedding,
        )
        self.assertFalse(met)
        # El backend de embedding no debe haber sido llamado
        mock_embedding.embed_text.assert_not_called()

    def test_reversibility_restricted_to_event(self):
        """Verifica que la reversibilidad active -> unknown solo aplica a type == Event."""
        event_blk = {
            "id": "ev_temp",
            "type": "Event",
            "state": "active",
            "active_conditions": [
                {"conditions": [{"entity_type": "place", "entity_id": "p_02", "sub_condition": "current_location"}]}
            ],
        }
        quest_blk = {
            "id": "q_perm",
            "type": "Quest",
            "state": "active",
            "active_conditions": [
                {"conditions": [{"entity_type": "place", "entity_id": "p_02", "sub_condition": "current_location"}]}
            ],
        }
        self.ctrl.game_state.loreblocks.active.extend([event_blk, quest_blk])

        # Jugador sigue en p_01 (condición p_02 no se cumple)
        LoreStateMachine.execute_cycle(self.ctrl)

        # Event revierte a unknown
        unknown_ids = {b["id"] for b in self.ctrl.game_state.loreblocks.unknown}
        self.assertIn("ev_temp", unknown_ids)

        # Quest permanece en active (no revierte)
        active_ids = {b["id"] for b in self.ctrl.game_state.loreblocks.active}
        self.assertIn("q_perm", active_ids)

    def test_hook_resolver_precedence_and_depth(self):
        """Verifica que HookResolver prioriza transición sobre armado y mayor profundidad jerárquica."""
        from engines.game.lore.hooks import HookResolver
        from engines.game.lore.library import LoreLibrary

        # Bloque padre profundidad 0, bloque hijo profundidad 1
        b_parent = {"id": "b_parent", "parent_id": None}
        b_child = {"id": "b_child", "parent_id": "b_parent"}
        library = LoreLibrary([b_parent, b_child])

        # 1. Empate de profundidad con armed vs transition
        armed = [("b_child", {"action": "hook", "target": "npc_bardo", "directive": "Dir Armado"})]
        trans = [("b_parent", {"action": "hook", "target": "npc_bardo", "directive": "Dir Transición"})]
        res = HookResolver.resolve_hook(trans, armed, "npc_bardo", "TALK", library, self.ctrl)
        self.assertIsNotNone(res)
        self.assertEqual(res.directive, "Dir Transición")

        # 2. Desempate por profundidad dentro de armed
        armed_both = [
            ("b_parent", {"action": "hook", "target": "npc_bardo", "directive": "Dir Padre"}),
            ("b_child", {"action": "hook", "target": "npc_bardo", "directive": "Dir Hijo"}),
        ]
        res_depth = HookResolver.resolve_hook([], armed_both, "npc_bardo", "TALK", library, self.ctrl)
        self.assertIsNotNone(res_depth)
        self.assertEqual(res_depth.directive, "Dir Hijo")

        # 3. No se resuelve si la acción es MOVE
        res_move = HookResolver.resolve_hook([], armed_both, "npc_bardo", "MOVE", library, self.ctrl)
        self.assertIsNone(res_move)

    def test_rag_hook_isolated_to_trigger_turn_and_not_subsequent_turns(self):
        """Verifica que un bloque con antena RAG solo inyecta hook cuando RAG se cumple."""
        rag_block = {
            "id": "blk_rag_secreto",
            "name": "Secreto RAG",
            "type": "Quest",  # Quest no revierte a unknown
            "state": "active",
            "active_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["donde esta el castillo"],
                    "conditions": [
                        {"entity_type": "npc", "entity_id": "npc_bardo", "sub_condition": "talk"}
                    ],
                }
            ],
            "active_effects": [
                {"action": "hook", "target": "npc_bardo", "directive": "Dile que el castillo está al norte"}
            ],
            "done_conditions": [],
        }
        self.ctrl.game_state.loreblocks.active = [rag_block]
        self.ctrl.game_state.player_state = "TALK"
        self.ctrl.game_state.player_target = "npc_bardo"

        # Turno 1: Jugador dispara la antena RAG
        res1 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="donde esta el castillo",
            precomputed_scores={"donde esta el castillo": 0.95},
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertEqual(res1.injected_directive, "Dile que el castillo está al norte")

        # Turno 2: Jugador sigue la conversación sin disparar la antena ("gracias")
        res2 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="muchas gracias bardo",
            precomputed_scores={"muchas gracias bardo": 0.10},
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertIsNone(res2.injected_directive)

        # Turno 3: Jugador habla sin input textual
        res3 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="",
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertIsNone(res3.injected_directive)

        # Turno 4: Jugador vuelve a preguntar y dispara la antena RAG de nuevo
        res4 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="donde esta el castillo",
            precomputed_scores={"donde esta el castillo": 0.95},
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertEqual(res4.injected_directive, "Dile que el castillo está al norte")

    def test_non_rag_hook_persists_in_armed_state(self):
        """Verifica que un bloque active sin antena RAG mantiene su hook armado persistente."""
        ambient_block = {
            "id": "blk_ambient",
            "name": "Guía Bardo",
            "type": "Quest",
            "state": "active",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {"entity_type": "npc", "entity_id": "npc_bardo", "sub_condition": "talk"}
                    ],
                }
            ],
            "active_effects": [
                {"action": "hook", "target": "npc_bardo", "directive": "El bardo canta sobre la reina"}
            ],
            "done_conditions": [],
        }
        self.ctrl.game_state.loreblocks.active = [ambient_block]
        self.ctrl.game_state.player_state = "TALK"
        self.ctrl.game_state.player_target = "npc_bardo"

        # Turno 1
        res1 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="hola bardo",
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertEqual(res1.injected_directive, "El bardo canta sobre la reina")

        # Turno 2 (sigue conversación)
        res2 = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="qué bonita canción",
            active_entity_id="npc_bardo",
            action_name="TALK",
        )
        self.assertEqual(res2.injected_directive, "El bardo canta sobre la reina")

    def test_push_action_isolation_not_treated_as_hook(self):
        """Verifica que un efecto con action='push' no se clasifique como hook ni contamine el turno del jugador."""
        push_block = {
            "id": "blk_push_only",
            "name": "Guardia Alerta",
            "type": "Task",
            "state": "unknown",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "push",
                    "target": "npc_bardo",
                    "directive": "¡Alto ahí, forastero!",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
        }
        self.ctrl.game_state.loreblocks.unknown = [push_block]

        # El jugador habla con el bardo
        res = LoreStateMachine.execute_cycle(
            self.ctrl,
            eval_query="hola",
            active_entity_id="npc_bardo",
            action_name="TALK",
            source="PLAYER",
        )

        # El push NO debe haberse inyectado como hook en el turno del jugador
        self.assertIsNone(res.injected_directive)
        self.assertFalse(res.bypass_llm)
        self.assertIsNone(res.bypass_text)

        # Pero SÍ debe haberse encolado como acción autónoma push
        self.assertEqual(len(res.autonomous_push_actions), 1)
        self.assertEqual(res.autonomous_push_actions[0].action, "TALK")
        self.assertEqual(res.autonomous_push_actions[0].target, "npc_bardo")
        self.assertEqual(res.autonomous_push_actions[0].directive, "¡Alto ahí, forastero!")
        self.assertTrue(res.autonomous_push_actions[0].bypass_llm)

    def test_push_action_target_resolution_by_id_and_name(self):
        """Verifica que LoreEffectApplier resuelva objetivos tanto por ID como por Nombre de entidades."""
        auto_pushes = []

        # 1. Por ID de NPC
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "npc_bardo", "directive": "D1"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "TALK")
        self.assertEqual(auto_pushes[-1].target, "npc_bardo")

        # 2. Por Nombre de NPC
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "Bardo", "directive": "D2"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "TALK")
        self.assertEqual(auto_pushes[-1].target, "npc_bardo")

        # 3. Por ID de Lugar
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "p_02", "directive": "D3"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "LOOK")
        self.assertEqual(auto_pushes[-1].target, "p_02")

        # 4. Por Nombre de Lugar
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "Bosque", "directive": "D4"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "LOOK")
        self.assertEqual(auto_pushes[-1].target, "p_02")

        # 5. Por ID de Ítem
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "item_llave", "directive": "D5"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "LOOK")
        self.assertEqual(auto_pushes[-1].target, "item_llave")

        # 6. Por Nombre de Ítem
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "Llave", "directive": "D6"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "LOOK")
        self.assertEqual(auto_pushes[-1].target, "item_llave")

        # 7. Fallback sin target o desconocido -> LOOK a current_location
        LoreEffectApplier.apply_effects(
            [{"action": "push", "target": "Inexistente", "directive": "D7"}],
            self.ctrl,
            auto_pushes,
        )
        self.assertEqual(auto_pushes[-1].action, "LOOK")
        self.assertEqual(auto_pushes[-1].target, self.ctrl.game_state.current_location)

    def test_popup_does_not_generate_autonomous_push_actions(self):
        """Verifica que bloques de tipo popup no generen acciones autónomas de push."""
        pop_blk = {
            "id": "pop_01",
            "name": "Popup Test",
            "type": "popup",
            "title": "Aviso Modal",
            "description": "Contenido del aviso",
            "state": "unknown",
            "active_conditions": [],
            "effects": [{"action": "push", "target": "npc_bardo", "directive": "No deberías ver esto"}],
        }
        self.ctrl.game_state.loreblocks.unknown = [pop_blk]

        res = LoreStateMachine.execute_cycle(self.ctrl)
        self.assertEqual(len(res.popups), 1)
        self.assertEqual(res.popups[0][0], "Aviso Modal")
        self.assertEqual(len(res.autonomous_push_actions), 0)

    def test_push_action_triggered_after_player_move_in_hsm(self):
        """Verifica que tras un MOVE que activa una tarea en el lugar destino, se despache el push."""
        quest = {
            "id": "q_01",
            "name": "Misión Castillo",
            "type": "Quest",
            "state": "active",
            "active_conditions": [],
            "done_conditions": [],
        }
        task = {
            "id": "t_01",
            "name": "Guardia en Bosque",
            "type": "Task",
            "parent_id": "q_01",
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {"entity_type": "place", "entity_id": "p_02", "sub_condition": "current_location"}
                    ],
                }
            ],
            "active_effects": [
                {
                    "action": "push",
                    "target": "Bardo",
                    "directive": "¡Bienvenido al bosque!",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
        }
        self.ctrl.game_state.loreblocks.active = [quest]
        self.ctrl.game_state.loreblocks.unknown = [task]

        # Simular movimiento a p_02
        self.ctrl.set_current_location("p_02")
        res = LoreStateMachine.execute_cycle(
            self.ctrl,
            action_name="MOVE",
            active_entity_id="p_02",
            source="PLAYER",
        )

        self.assertEqual(len(res.autonomous_push_actions), 1)
        push = res.autonomous_push_actions[0]
        self.assertEqual(push.action, "TALK")
        self.assertEqual(push.target, "npc_bardo")
        self.assertEqual(push.directive, "¡Bienvenido al bosque!")
        self.assertTrue(push.bypass_llm)


if __name__ == "__main__":
    unittest.main()
