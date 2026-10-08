"""Pruebas unitarias para el ciclo de vida de acciones Hook y Bypass de LLM."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from domains.game_state import LoreBlockHierarchy
from domains.items import Item
from domains.npcs import NPC
from domains.player import Player
from domains.world import Connection, Location, Place, World
from engines.game.engine import GameEngine
from engines.game.state_controller import GameStateController


class TestHookBypassLifecycle(unittest.TestCase):
    """Verifica las 5 reglas canónicas de hooks y bypass_llm."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        self.p1 = Place(
            id="p1",
            name="Plaza",
            description="La plaza central.",
            connections={"p2": Connection(target="p2", distance=100, terrain_type="village")},
        )
        self.p2 = Place(
            id="p2",
            name="Casa",
            description="Una casa acogedora.",
            connections={"p1": Connection(target="p1", distance=100, terrain_type="village")},
        )

        self.loc = Location(id="loc1", name="Villa", description="Una villa tranquila", places=[self.p1, self.p2])
        self.world = World(id="w1", name="Mundo", description="Mundo fantástico", locations=[self.loc])

        self.player = Player(
            id="player1",
            name="Aventurero",
            description="El protagonista",
            gold=10,
            inventory=[],
            initial_location="p1",
        )

        self.sabio = NPC(id="npc_sabio", name="Sabio", description="Un anciano sabio", initial_location="p2")
        self.llave = Item(id="item_llave", name="Llave Antigua", description="Una llave oxidada", initial_location="p2")
        self.puerta = Item(id="item_door", name="Puerta", description="Una gran puerta de madera", initial_location="p2")

        self.hierarchy = LoreBlockHierarchy(
            active=[],
            done=[],
            unknown=[],
            popups=[],
        )

        self.controller = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=[self.sabio],
            items=[self.llave, self.puerta],
            loreblocks_hierarchy=self.hierarchy,
            adventure_path=self.temp_dir,
            elapsed_time_enabled=True,
        )

        self.mock_transformer = MagicMock()
        self.mock_transformer.execute.return_value = {"msg": "Respuesta generada por el LLM."}

        self.engine = GameEngine(
            game_state_controller=self.controller,
            transformer_engine=self.mock_transformer,
        )

    def tearDown(self):
        if self.engine._running:
            self.engine.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hook_not_triggered_on_move(self):
        """Regla 1: Un hook con bypass_llm: True NO se ejecuta al moverse (MOVE), aunque el bloque se active."""
        block_llave = {
            "id": "blk_llave",
            "name": "Llave en Casa",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p2",
                            "sub_condition": "current_location",
                        }
                    ]
                }
            ],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "¿Quieres coger la llave del suelo?",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        self.controller.game_state.loreblocks.unknown.append(block_llave)

        # Jugador hace MOVE a Casa (p2)
        res = self.engine.execute_turn(action="MOVE", target="p2")

        # El bloque debe haber pasado a 'active'
        active_ids = [b["id"] for b in self.controller.game_state.loreblocks.active]
        self.assertIn("blk_llave", active_ids)

        # Pero el turno es la narrativa normal de MOVE del Dungeon Master, NO el hook de la llave
        self.assertEqual(res.output.author, "Dungeon Master")
        self.assertNotIn("¿Quieres coger la llave", res.output.msg)
        # El LLM sí fue llamado para la narrativa de MOVE
        self.mock_transformer.execute.assert_called_once()
        self.assertIsNotNone(res.debug.prompt)

    def test_hook_triggered_on_look_with_bypass(self):
        """Regla 1 y 3: Un hook con bypass_llm: True se dispara al hacer LOOK sobre el target y emite texto literal."""
        block_llave = {
            "id": "blk_llave",
            "name": "Llave en Casa",
            "type": "Event",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "¿Quieres coger la llave del suelo?",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        self.controller.game_state.loreblocks.active.append(block_llave)
        self.controller.set_current_location("p2")

        # Jugador interactúa con la llave mediante LOOK
        res = self.engine.execute_turn(action="LOOK", target="item_llave")

        # Debe entregar exactamente la directiva y omitir el LLM
        self.assertEqual(res.output.author, "Dungeon Master")
        self.assertEqual(res.output.msg, "¿Quieres coger la llave del suelo?")
        self.assertIsNone(res.debug.prompt)
        self.mock_transformer.execute.assert_not_called()

        # Regla 3: Si se vuelve a interactuar, entrega exactamente el mismo texto
        res2 = self.engine.execute_turn(action="LOOK", target="item_llave")
        self.assertEqual(res2.output.msg, "¿Quieres coger la llave del suelo?")
        self.assertIsNone(res2.debug.prompt)
        self.mock_transformer.execute.assert_not_called()

    def test_hook_triggered_on_talk_with_bypass_author_npc(self):
        """Un hook con bypass_llm: True hacia un NPC asigna el autor al nombre del NPC."""
        block_sabio = {
            "id": "blk_sabio",
            "name": "Consejo del Sabio",
            "type": "Event",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "npc_sabio",
                    "directive": "Escucha atentamente el secreto de la montaña.",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        self.controller.game_state.loreblocks.active.append(block_sabio)
        self.controller.set_current_location("p2")

        # Jugador interactúa con el Sabio mediante TALK
        res = self.engine.execute_turn(action="TALK", target="npc_sabio")

        self.assertEqual(res.output.author, "Sabio")
        self.assertEqual(res.output.msg, "Escucha atentamente el secreto de la montaña.")
        self.assertIsNone(res.debug.prompt)
        self.mock_transformer.execute.assert_not_called()

    def test_hook_triggered_on_look_without_bypass(self):
        """Un hook con bypass_llm: False inyecta la directiva al LLM sin omitir la llamada."""
        block_llave = {
            "id": "blk_llave",
            "name": "Llave en Casa",
            "type": "Event",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "Describe el brillo metálico de la llave.",
                    "bypass_llm": False,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        self.controller.game_state.loreblocks.active.append(block_llave)
        self.controller.set_current_location("p2")

        res = self.engine.execute_turn(action="LOOK", target="item_llave")

        # No hay bypass de LLM (se construye el prompt con la directiva inyectada)
        self.assertIsNotNone(res.debug.prompt)
        self.assertIn("Describe el brillo metálico", res.debug.prompt)
        self.mock_transformer.execute.assert_called_once()

    def test_hook_collision_deepest_child_wins(self):
        """Regla 5: Colisión de hooks hacia la misma entidad: gana el bloque hijo más profundo."""
        block_padre = {
            "id": "blk_padre",
            "name": "Misión General",
            "type": "Quest",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "npc_sabio",
                    "directive": "Diálogo genérico del Sabio (Padre).",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        block_hijo = {
            "id": "blk_hijo",
            "name": "Paso Específico",
            "type": "Task",
            "parent_id": "blk_padre",
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "npc_sabio",
                    "directive": "Diálogo específico urgente del Sabio (Hijo).",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        # Inserción en cualquier orden en active
        self.controller.game_state.loreblocks.active = [block_padre, block_hijo]
        self.controller.set_current_location("p2")

        res = self.engine.execute_turn(action="TALK", target="npc_sabio")

        # Debe ganar el hijo (depth 1 > depth 0)
        self.assertEqual(res.output.author, "Sabio")
        self.assertEqual(res.output.msg, "Diálogo específico urgente del Sabio (Hijo).")
        self.mock_transformer.execute.assert_not_called()

    def test_done_effects_bypass_emitted_on_completion(self):
        """Regla 4: done_effects con bypass_llm: True emiten su mensaje directamente en el turno que completan."""
        block_quest = {
            "id": "blk_quest",
            "name": "Recoger Llave",
            "type": "Task",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [],
            "done_conditions": [
                {
                    "conditions": [
                        {
                            "entity_type": "item",
                            "entity_id": "item_llave",
                            "sub_condition": "have",
                        }
                    ]
                }
            ],
            "done_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "Has cogido la llave y la guardas en el inventario.",
                    "bypass_llm": True,
                }
            ],
        }
        self.controller.game_state.loreblocks.active.append(block_quest)
        self.controller.set_current_location("p2")

        # Simulamos que el jugador obtiene la llave en este turno y mira la llave
        self.controller.game_state.inventory.append("item_llave")
        res = self.engine.execute_turn(action="LOOK", target="item_llave")

        # El bloque debe estar en 'done'
        done_ids = [b["id"] for b in self.controller.game_state.loreblocks.done]
        self.assertIn("blk_quest", done_ids)

        # El mensaje del turno debe ser el de done_effects
        self.assertEqual(res.output.msg, "Has cogido la llave y la guardas en el inventario.")
        self.mock_transformer.execute.assert_not_called()

    def test_cascade_conversational_input_isolation(self):
        """Asegura que un input conversacional (p. ej. 'si') no se filtre a bloques recién activados en cascada."""
        block_key = {
            "id": "blk_key",
            "name": "Coger Llave",
            "type": "Event",
            "parent_id": None,
            "state": "active",
            "active_conditions": [],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "¿Quieres coger la llave del suelo?",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["si", "la cojo"],
                    "conditions": [],
                }
            ],
            "done_effects": [
                {
                    "action": "hook",
                    "target": "item_llave",
                    "directive": "Has cogido la llave.",
                    "bypass_llm": True,
                    "give_items": ["item_llave"],
                }
            ],
        }

        block_door = {
            "id": "blk_door",
            "name": "Abrir Puerta",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {
                            "entity_type": "item",
                            "entity_id": "item_llave",
                            "sub_condition": "have",
                        }
                    ],
                }
            ],
            "active_effects": [
                {
                    "action": "hook",
                    "target": "item_door",
                    "directive": "¿Quieres abrir la puerta?",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["si", "abrir"],
                    "conditions": [],
                }
            ],
            "done_effects": [
                {
                    "action": "hook",
                    "target": "item_door",
                    "directive": "Has abierto la puerta.",
                    "bypass_llm": True,
                }
            ],
        }

        self.controller.game_state.loreblocks.active.append(block_key)
        self.controller.game_state.loreblocks.unknown.append(block_door)
        self.controller.set_current_location("p2")

        # 1. Jugador mira la llave (LOOK -> item_llave)
        res0 = self.engine.execute_turn(action="LOOK", target="item_llave")
        self.assertEqual(res0.output.msg, "¿Quieres coger la llave del suelo?")

        # 2. Jugador responde 'si' a la llave
        res1 = self.engine.execute_turn(action="", target="", player_input="si")

        # El resultado debe ser el de la llave, NO el de la puerta
        self.assertEqual(res1.output.msg, "Has cogido la llave.")
        self.assertIn("blk_key", [b["id"] for b in self.controller.game_state.loreblocks.done])
        # blk_door debe estar activo tras la cascada, pero NO completado
        self.assertIn("blk_door", [b["id"] for b in self.controller.game_state.loreblocks.active])
        self.assertNotIn("blk_door", [b["id"] for b in self.controller.game_state.loreblocks.done])

        # 3. Jugador mira la puerta (LOOK -> item_door)
        res2 = self.engine.execute_turn(action="LOOK", target="item_door")
        self.assertEqual(res2.output.msg, "¿Quieres abrir la puerta?")

        # 4. Jugador responde 'si' a la puerta en un nuevo turno
        res3 = self.engine.execute_turn(action="", target="", player_input="si")
        self.assertEqual(res3.output.msg, "Has abierto la puerta.")
        self.assertIn("blk_door", [b["id"] for b in self.controller.game_state.loreblocks.done])


if __name__ == "__main__":
    unittest.main()

