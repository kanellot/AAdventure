"""Pruebas unitarias para el nuevo GameEngine."""

import shutil
import tempfile
import unittest

from domains.game_state import LoreBlockHierarchy
from domains.items import Item
from domains.npcs import NPC
from domains.player import Player
from domains.world import Connection, Location, Place, World
from engines.events import EngineEventListener
from engines.game.engine import GameEngine
from engines.game.state_controller import GameStateController


class MockEventListener(EngineEventListener):
    """Observador de prueba para registrar eventos emitidos por GameEngine."""

    def __init__(self):
        self.turns_completed = []
        self.thinking_events = []
        self.errors = []

    def on_turn_completed(self, turn_result):
        self.turns_completed.append(turn_result)

    def on_thinking_changed(self, event_json):
        self.thinking_events.append(event_json)

    def on_error(self, task_id, error_message, error_code):
        self.errors.append((task_id, error_message, error_code))


class TestGameEngine(unittest.TestCase):
    """Pruebas completas del pipeline determinista de turnos y ciclo de vida de GameEngine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Grafo de Lugares:
        # P1 (Plaza) <--(100m, village)--> P2 (Taberna) <--(500m, forest)--> P3 (Bosque)
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
            connections={
                "p1": Connection(target="p1", distance=100, terrain_type="village"),
                "p3": Connection(target="p3", distance=500, terrain_type="forest"),
            },
        )
        self.p3 = Place(
            id="p3",
            name="Bosque Profundo",
            description="Un bosque oscuro y peligroso.",
            connections={"p2": Connection(target="p2", distance=500, terrain_type="forest")},
        )

        self.loc = Location(id="loc1", name="Aldea", description="Una aldea tranquila",
                            places=[self.p1, self.p2, self.p3])
        self.world = World(id="w1", name="Mundo", description="Un mundo fantástico", locations=[self.loc])

        self.player = Player(
            id="player1",
            name="Héroe",
            description="El protagonista",
            gold=50,
            inventory=["item_dagger"],
            initial_location="p1",
        )

        self.npc1 = NPC(id="npc_tom", name="Tom", description="Un aldeano amistoso", initial_location="p1")
        self.npc2 = NPC(id="npc_bartender", name="Tabernero", description="El dueño de la taberna",
                        initial_location="p2")

        self.item1 = Item(id="item_apple", name="Manzana", description="Fruta roja", initial_location="p1")
        self.item2 = Item(id="item_ale", name="Cerveza", description="Bebida espumosa", initial_location="p2")

        self.hierarchy = LoreBlockHierarchy(
            active=[{"id": "q1", "name": "Misión 1", "type": "Quest", "description": "Salva la aldea"}],
            done=[],
            unknown=[],
        )

        self.controller = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=[self.npc1, self.npc2],
            items=[self.item1, self.item2],
            loreblocks_hierarchy=self.hierarchy,
            adventure_path=self.temp_dir,
            elapsed_time_enabled=True,
        )

        self.engine = GameEngine(game_state_controller=self.controller)

    def tearDown(self):
        if self.engine._running:
            self.engine.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_strict_free_text_rejection_in_explore(self):
        """El texto libre en EXPLORE debe ser estrictamente rechazado."""
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")
        result = self.engine.execute_turn(action="", player_input="Hola, hay alguien aquí?")

        self.assertEqual(result.output.player_state, "EXPLORE")
        self.assertEqual(result.output.author, "SYSTEM")
        self.assertIn("Debes seleccionar una acción", result.output.msg)
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")

    def test_valid_move_and_terrain_travel_time(self):
        """Un MOVE válido avanza de lugar, progresa la niebla de guerra y suma tiempo según terreno."""
        initial_time = self.controller.game_state.current_time
        result = self.engine.execute_turn(action="MOVE", target="p2")

        self.assertEqual(self.controller.game_state.current_location, "p2")
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")
        self.assertIsNone(self.controller.game_state.player_target)
        self.assertIn("Llegas a Taberna", result.output.msg)
        self.assertEqual(result.output.author, "Dungeon Master")

        # Niebla de guerra: P2 es visited, P3 es visible
        places_by_id = {p.id: p for loc in result.map.locations for p in loc.places}
        self.assertEqual(places_by_id["p2"].status, "visited")
        self.assertEqual(places_by_id["p3"].status, "visible")

        # Comprobar avance de tiempo (100m a 4.5km/h terreno village ~ 1.33 min)
        self.assertNotEqual(self.controller.game_state.current_time, initial_time)

    def test_move_with_empty_target(self):
        """MOVE sin objetivo debe ser rechazado."""
        result = self.engine.execute_turn(action="MOVE", target="")
        self.assertEqual(result.output.author, "SYSTEM")
        self.assertIn("Debes indicar un destino", result.output.msg)

    def test_move_blocked_first_step(self):
        """Si el primer paso está bloqueado, no hay avance efectivo y se emite error."""
        self.controller.block_place("p2")
        result = self.engine.execute_turn(action="MOVE", target="p2")

        self.assertEqual(self.controller.game_state.current_location, "p1")
        self.assertEqual(result.output.author, "SYSTEM")
        self.assertIn("está bloqueado en 'Taberna'", result.output.msg)

    def test_move_blocked_intermediate_step_advances_partially(self):
        """Si el camino contiene al menos 1 paso libre antes del bloqueo, avanza hasta allí."""
        # Bloquear P3. Destino del jugador es P3 desde P1. Camino: P1 -> P2 -> [P3 bloqueado]
        self.controller.block_place("p3")
        result = self.engine.execute_turn(action="MOVE", target="p3")

        # Debe avanzar a P2
        self.assertEqual(self.controller.game_state.current_location, "p2")
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")
        self.assertIn("Avanzas por el camino hasta llegar a Taberna", result.output.msg)
        self.assertIn("el paso hacia 'Bosque Profundo' se encuentra bloqueado", result.output.msg)

    def test_talk_to_local_npc_and_dialogue_exchange(self):
        """Conversar con un NPC local cambia a TALK, añade tiempo y registra el historial."""
        # Paso 1: Acción TALK
        result = self.engine.execute_turn(action="TALK", target="npc_tom")
        self.assertEqual(self.controller.game_state.player_state, "TALK")
        self.assertEqual(self.controller.game_state.player_target, "npc_tom")
        self.assertEqual(result.output.author, "Tom")
        self.assertIn("¡Saludos", result.output.msg)

        # Paso 2: Mensaje de texto libre en estado TALK
        result2 = self.engine.execute_turn(action="", player_input="¿Has visto algo extraño?")
        self.assertEqual(self.controller.game_state.player_state, "TALK")
        self.assertEqual(self.controller.game_state.player_target, "npc_tom")
        self.assertEqual(result2.output.author, "Tom")

        # Verificar historial en GameState
        convs = self.controller.game_state.conversations.get("npc_tom", [])
        self.assertGreaterEqual(len(convs), 2)
        self.assertEqual(convs[-2], {"player": "¿Has visto algo extraño?"})
        self.assertIn("Tom", convs[-1])

    def test_talk_to_absent_npc_rejected(self):
        """Intentar hablar con un NPC que no está en el lugar actual debe ser rechazado."""
        # npc_bartender está en p2, el jugador está en p1
        result = self.engine.execute_turn(action="TALK", target="npc_bartender")
        self.assertEqual(result.output.author, "SYSTEM")
        self.assertIn("no se encuentra aquí", result.output.msg)
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")

    def test_look_default_target_current_location(self):
        """LOOK sin objetivo explícito inspecciona el current_location."""
        result = self.engine.execute_turn(action="LOOK", target="")
        self.assertEqual(self.controller.game_state.player_state, "LOOK")
        self.assertEqual(self.controller.game_state.player_target, "p1")
        self.assertEqual(result.output.author, "Dungeon Master")
        self.assertIn("Miras a tu alrededor en Plaza Mayor", result.output.msg)

    def test_look_specific_item_and_unreachable_entity(self):
        """LOOK inspecciona ítems en el lugar y rechaza entidades inalcanzables."""
        # item_apple está en p1
        result = self.engine.execute_turn(action="LOOK", target="item_apple")
        self.assertEqual(result.output.author, "Dungeon Master")
        self.assertIn("Examinas Manzana", result.output.msg)

        # item_ale está en p2, no en p1 ni en inventario -> no alcanzable
        result_unreachable = self.engine.execute_turn(action="LOOK", target="item_ale")
        self.assertEqual(result_unreachable.output.author, "SYSTEM")
        self.assertIn("no está a tu alcance", result_unreachable.output.msg)

    def test_universal_disengagement(self):
        """Cualquier acción desengancha el estado actual y limpia o actualiza el objetivo."""
        # 1. Iniciar TALK
        self.engine.execute_turn(action="TALK", target="npc_tom")
        self.assertEqual(self.controller.game_state.player_state, "TALK")
        self.assertEqual(self.controller.game_state.player_target, "npc_tom")

        # 2. Desenganchar con MOVE
        self.engine.execute_turn(action="MOVE", target="p2")
        self.assertEqual(self.controller.game_state.player_state, "EXPLORE")
        self.assertIsNone(self.controller.game_state.player_target)
        self.assertEqual(self.controller.game_state.current_location, "p2")

        # 3. Iniciar LOOK en P2
        self.engine.execute_turn(action="LOOK", target="item_ale")
        self.assertEqual(self.controller.game_state.player_state, "LOOK")
        self.assertEqual(self.controller.game_state.player_target, "item_ale")

        # 4. Desenganchar LOOK hablando con el Tabernero en P2
        self.engine.execute_turn(action="TALK", target="npc_bartender")
        self.assertEqual(self.controller.game_state.player_state, "TALK")
        self.assertEqual(self.controller.game_state.player_target, "npc_bartender")

    def test_worker_thread_and_listener_dispatch(self):
        """El worker en segundo plano procesa tareas encoladas y notifica a los listeners."""
        listener = MockEventListener()
        self.engine.add_listener(listener)
        self.engine.start()

        task_id = self.engine.enqueue_action("MOVE", "p2")
        self.assertIsNotNone(task_id)

        # Esperar a que el worker procese la tarea
        self.engine.task_queue.join()

        self.assertEqual(len(listener.turns_completed), 1)
        res = listener.turns_completed[0]
        self.assertEqual(res.output.player_state, "EXPLORE")
        self.assertEqual(self.controller.game_state.current_location, "p2")
        self.assertGreater(len(listener.thinking_events), 0)

        self.engine.stop()

    def test_popup_target_agnostic_and_turn_preserved(self):
        """Un popup sin target y sin efectos se dispara modalmente sin interrumpir ni sobrescribir la narrativa del turno."""
        # Agregamos un popup en unknown con active_conditions de llegar a p2
        popup_block = {
            "id": "popup_test",
            "name": "¡Bienvenido a la Taberna!",
            "title": "Aviso de Taberna",
            "description": "Has descubierto un rincón concurrido y acogedor.",
            "type": "popup",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p2",
                            "sub_condition": "current_location",
                            "value": None,
                            "is_negated": False,
                        }
                    ],
                }
            ],
            "done_conditions": [],
            "effects": [],
        }
        self.controller.game_state.loreblocks.unknown.append(popup_block)

        # Moverse a p2
        res = self.engine.execute_turn(action="MOVE", target="p2")

        # 1. El turno del jugador generó su narrativa normal sin ser sustituido
        self.assertEqual(res.output.author, "Dungeon Master")
        self.assertEqual(res.output.type, "msg")
        self.assertIn("Taberna", res.output.msg)
        self.assertEqual(self.controller.game_state.current_location, "p2")

        # 2. El popup se adjunta como evento modal simultáneo
        self.assertEqual(res.output.popup_title, "Aviso de Taberna")
        self.assertEqual(res.output.popup_message, "Has descubierto un rincón concurrido y acogedor.")

        # 3. El popup transiciona directamente a done (no queda en active ni unknown)
        unknown_ids = {b["id"] for b in self.controller.game_state.loreblocks.unknown}
        active_ids = {b["id"] for b in self.controller.game_state.loreblocks.active}
        done_ids = {b["id"] for b in self.controller.game_state.loreblocks.done}
        self.assertNotIn("popup_test", unknown_ids)
        self.assertNotIn("popup_test", active_ids)
        self.assertIn("popup_test", done_ids)

    def test_execute_turn_0_intro_and_popups(self):
        """Verifica que el Turno 0 emite world.initial_text y evalúa popups sin efectos colaterales."""
        self.world.initial_text = "El alba despunta sobre las torres de la aldea..."

        popup_block = {
            "id": "popup_inicio",
            "name": "Prólogo",
            "title": "Bienvenida a la partida",
            "description": "Una aventura sin precedentes está a punto de comenzar.",
            "type": "popup",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p1",
                            "sub_condition": "current_location",
                            "value": None,
                            "is_negated": False,
                        }
                    ],
                }
            ],
            "done_conditions": [],
            "effects": [],
        }

        standard_quest = {
            "id": "quest_inicio",
            "name": "Misión Inicial",
            "title": "Aviso Misión",
            "description": "No debe activarse en Turno 0.",
            "type": "Quest",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {
                            "entity_type": "place",
                            "entity_id": "p1",
                            "sub_condition": "current_location",
                            "value": None,
                            "is_negated": False,
                        }
                    ],
                }
            ],
            "done_conditions": [],
            "effects": [],
        }

        self.controller.game_state.loreblocks.unknown.append(popup_block)
        self.controller.game_state.loreblocks.unknown.append(standard_quest)

        initial_gold = self.controller.game_state.gold
        initial_inv = list(self.controller.game_state.inventory.items)

        # Ejecutar Turno 0
        res = self.engine.execute_turn_0()

        # 1. Narrativa: Dungeon Master con el texto inicial de World
        self.assertEqual(res.output.author, "Dungeon Master")
        self.assertEqual(res.output.type, "msg")
        self.assertEqual(res.output.msg, "El alba despunta sobre las torres de la aldea...")
        self.assertEqual(res.output.player_state, "EXPLORE")

        # 2. Popup evaluado y disparado
        self.assertEqual(res.output.popup_title, "Bienvenida a la partida")
        self.assertEqual(res.output.popup_message, "Una aventura sin precedentes está a punto de comenzar.")

        # 3. Popup pasa a 'done', bloque estándar permanece en 'unknown'
        unknown_ids = {b["id"] for b in self.controller.game_state.loreblocks.unknown}
        done_ids = {b["id"] for b in self.controller.game_state.loreblocks.done}
        self.assertIn("popup_inicio", done_ids)
        self.assertNotIn("popup_inicio", unknown_ids)
        self.assertIn("quest_inicio", unknown_ids)

        # 4. Sin efectos sobre inventario u oro
        self.assertEqual(self.controller.game_state.gold, initial_gold)
        self.assertEqual(self.controller.game_state.inventory.items, initial_inv)

    def test_loreblocks_without_conditions_activate_hierarchically_and_accessible_projection(self):
        """Verifica que bloques sin condiciones activan en cascada HSM y la proyección calcula is_accessible correctamente."""
        # Configurar un Chapter raíz sin condiciones (lista con grupo vacío como genera el editor)
        chapter = {
            "id": "c_raiz",
            "name": "Capítulo Raíz",
            "title": "Capítulo Raíz",
            "description": "Capítulo sin condiciones",
            "type": "Chapter",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [{"rag_enabled": False, "trigger_phrases": [], "conditions": []}],
            "done_conditions": [],
            "effects": [],
        }
        # Quest hija sin condiciones
        quest = {
            "id": "q_hija",
            "name": "Misión Hija",
            "title": "Misión Hija",
            "description": "Misión hija de c_raiz",
            "type": "Quest",
            "parent_id": "c_raiz",
            "state": "unknown",
            "active_conditions": [],
            "done_conditions": [],
            "effects": [],
        }
        # Task nieta con condición
        task = {
            "id": "t_nieta",
            "name": "Tarea Nieta",
            "title": "Tarea Nieta",
            "description": "Tarea con condición",
            "type": "Task",
            "parent_id": "q_hija",
            "state": "unknown",
            "active_conditions": [
                {
                    "rag_enabled": False,
                    "trigger_phrases": [],
                    "conditions": [
                        {
                            "entity_type": "npc",
                            "entity_id": "guard",
                            "sub_condition": "talk",
                            "value": None,
                            "is_negated": False,
                        }
                    ],
                }
            ],
            "done_conditions": [],
            "effects": [],
        }

        self.controller.game_state.loreblocks.unknown = [chapter, quest, task]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # Ejecutar turno 1 (MOVE a p2)
        res = self.engine.execute_turn(action="MOVE", target="p2")

        active_ids = {b["id"] for b in self.controller.game_state.loreblocks.active}
        unknown_ids = {b["id"] for b in self.controller.game_state.loreblocks.unknown}

        # c_raiz y q_hija deben activarse automáticamente en cascada
        self.assertIn("c_raiz", active_ids)
        self.assertIn("q_hija", active_ids)
        # t_nieta permanece en unknown porque no se ha hablado con el guardia
        self.assertIn("t_nieta", unknown_ids)

        # Cuaderno debe contener la misión hija activa
        notebook_ids = {q.id for q in self.controller.game_state.notebook}
        self.assertIn("q_hija", notebook_ids)

        # Verificar proyección gráfica
        proj = self.engine.get_lore_graph_projection()
        proj_by_id = {b.id: b for b in proj.blocks}

        self.assertTrue(proj_by_id["c_raiz"].is_accessible)
        self.assertEqual(proj_by_id["c_raiz"].state, "active")

        self.assertTrue(proj_by_id["q_hija"].is_accessible)
        self.assertEqual(proj_by_id["q_hija"].state, "active")

        # t_nieta está en unknown pero es accesible porque su padre q_hija está en active
        self.assertTrue(proj_by_id["t_nieta"].is_accessible)
        self.assertEqual(proj_by_id["t_nieta"].state, "unknown")
        self.assertEqual(len(proj_by_id["t_nieta"].conditions), 1)
        self.assertFalse(proj_by_id["t_nieta"].conditions[0].is_met)

    def test_rag_evaluation_includes_accessible_unknown_loreblocks(self):
        """Verifica que bloques en unknown accesibles evalúan antenas RAG, proyectan en el debugger y activan."""
        block = {
            "id": "lb_info_castillo",
            "name": "Info Castillo",
            "title": "Info Castillo",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "threshold": 0.65,
            "active_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["Castillo del Rey", "donde encontrar castillo"],
                    "conditions": [],
                }
            ],
            "done_conditions": [],
            "effects": [
                {
                    "target": "npc_tom",
                    "action": "hook",
                    "directive": "Dile que el castillo está al norte",
                }
            ],
        }
        self.controller.game_state.loreblocks.unknown = [block]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # Jugador habla con npc_tom preguntando por el castillo
        res = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="donde encontrar castillo")

        # Verificar proyección RAG en el resultado
        self.assertIsNotNone(res.debug)
        self.assertIsNotNone(res.debug.rag_evaluation)
        rag_eval = res.debug.rag_evaluation
        self.assertEqual(rag_eval.matched_lore_id, "lb_info_castillo")
        self.assertEqual(rag_eval.injected_directive, "Dile que el castillo está al norte")
        self.assertEqual(rag_eval.active_entity_id, "npc_tom")

        # Verificar que el bloque transicionó a active en el estado del juego
        active_ids = {b["id"] for b in self.controller.game_state.loreblocks.active}
        self.assertIn("lb_info_castillo", active_ids)

        # Verificar antenas en la proyección diagnóstica
        antennas = {a.antenna: a for a in rag_eval.antennas}
        self.assertIn("donde encontrar castillo", antennas)
        win_ant = antennas["donde encontrar castillo"]
        self.assertTrue(win_ant.is_matched)
        self.assertTrue(win_ant.is_injected)
        self.assertTrue(win_ant.conditions_met)
        self.assertTrue(win_ant.affects_active_entity)

    def test_rag_hook_isolated_to_turn_and_not_injected_on_conversation_or_return(self):
        """Verifica que un hook RAG solo se inyecta en el turno que dispara el RAG y no al continuar o volver."""
        block = {
            "id": "lb_rumor_castillo",
            "name": "Rumor Castillo",
            "title": "Rumor Castillo",
            "type": "Quest",
            "parent_id": None,
            "threshold": 0.65,
            "active_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["donde encontrar castillo"],
                    "conditions": [],
                }
            ],
            "done_conditions": [],
            "effects": [
                {
                    "target": "npc_tom",
                    "directive": "Dile que el castillo está al norte",
                }
            ],
        }
        self.controller.game_state.loreblocks.unknown = [block]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # Turno 1: Jugador pregunta por el castillo -> RAG dispara e inyecta directriz
        res1 = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="donde encontrar castillo")
        self.assertEqual(res1.debug.rag_evaluation.injected_directive, "Dile que el castillo está al norte")

        # Turno 2: Jugador sigue la conversación sin preguntar por el castillo ("muchas gracias")
        # El bloque sigue en active, pero RAG NO se disparó -> NO se inyecta la directriz
        res2 = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="muchas gracias")
        self.assertIsNone(res2.debug.rag_evaluation.injected_directive)

        # Turno 3: Jugador se desplaza a otro lugar (p2)
        self.engine.execute_turn(action="MOVE", target="p2")

        # Turno 4: Jugador regresa (p1)
        self.engine.execute_turn(action="MOVE", target="p1")

        # Turno 5: Jugador habla con Tom diciendo "hola de nuevo" sin disparar RAG -> NO se inyecta
        res5 = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="hola de nuevo")
        self.assertIsNone(res5.debug.rag_evaluation.injected_directive)

        # Turno 6: Jugador vuelve a preguntar por el castillo -> RAG dispara e inyecta directriz
        res6 = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="donde encontrar castillo")
        self.assertEqual(res6.debug.rag_evaluation.injected_directive, "Dile que el castillo está al norte")

    def test_rag_evaluation_done_conditions_on_active_blocks(self):
        """Verifica que bloques en active evalúan sus done_conditions con RAG y completan a done."""
        block = {
            "id": "lb_quest_taberna",
            "name": "Misión Taberna",
            "title": "Misión Taberna",
            "type": "Quest",
            "parent_id": None,
            "state": "active",
            "threshold": 0.65,
            "active_conditions": [],
            "done_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["acepto el encargo", "cuenta conmigo"],
                    "conditions": [],
                }
            ],
            "effects": [],
        }
        self.controller.game_state.loreblocks.unknown = []
        self.controller.game_state.loreblocks.active = [block]
        self.controller.game_state.loreblocks.done = []

        res = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="acepto el encargo")

        self.assertIsNotNone(res.debug.rag_evaluation)
        self.assertEqual(res.debug.rag_evaluation.matched_lore_id, "lb_quest_taberna")

        # Debe haber transicionado a done
        done_ids = {b["id"] for b in self.controller.game_state.loreblocks.done}
        self.assertIn("lb_quest_taberna", done_ids)

    def test_rag_evaluation_conditions_not_met_flagged_correctly(self):
        """Verifica que si una antena hace match pero sus condiciones lógicas no se cumplen, se marca conditions_met=False."""
        block = {
            "id": "lb_secreto_bartender",
            "name": "Secreto Tabernero",
            "title": "Secreto Tabernero",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "threshold": 0.65,
            "active_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["hablar del tesoro", "secreto del pueblo"],
                    "conditions": [
                        {
                            "entity_type": "npc",
                            "entity_id": "npc_bartender",
                            "sub_condition": "talk",
                            "value": None,
                            "is_negated": False,
                        }
                    ],
                }
            ],
            "done_conditions": [],
            "effects": [{"target": "npc_bartender", "directive": "El tesoro está enterrado"}],
        }
        self.controller.game_state.loreblocks.unknown = [block]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # El jugador habla con npc_tom (NO con npc_bartender) diciendo la frase gatillo
        res = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="hablar del tesoro")

        rag_eval = res.debug.rag_evaluation
        self.assertIsNotNone(rag_eval)
        # No debe haber coincidencia ganadora porque no se cumplieron las condiciones
        self.assertIsNone(rag_eval.matched_lore_id)

        # En la lista de antenas, la condición debe aparecer como no cumplida
        antennas = {a.antenna: a for a in rag_eval.antennas}
        self.assertIn("hablar del tesoro", antennas)
        ant = antennas["hablar del tesoro"]
        self.assertFalse(ant.conditions_met)
        self.assertFalse(ant.is_matched)
        self.assertFalse(ant.is_injected)

        # El bloque debe seguir en unknown
        unknown_ids = {b["id"] for b in self.controller.game_state.loreblocks.unknown}
        self.assertIn("lb_secreto_bartender", unknown_ids)

    def test_rag_directive_targets_active_entity_specifically(self):
        """Verifica que ante un bloque con directivas para múltiples entidades, se inyecta la de la entidad activa."""
        block = {
            "id": "lb_info_doble",
            "name": "Info Doble",
            "title": "Info Doble",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "threshold": 0.65,
            "active_conditions": [
                {
                    "rag_enabled": True,
                    "trigger_phrases": ["donde esta el molino"],
                    "conditions": [],
                }
            ],
            "done_conditions": [],
            "effects": [
                {"target": "npc_tom", "directive": "Tom dice: ve por el camino sur"},
                {"target": "npc_bartender", "directive": "El tabernero dice: cruza el río"},
            ],
        }
        self.controller.game_state.loreblocks.unknown = [block]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # Hablar con npc_tom
        res_tom = self.engine.execute_turn(action="TALK", target="npc_tom", player_input="donde esta el molino")
        self.assertEqual(res_tom.debug.rag_evaluation.injected_directive, "Tom dice: ve por el camino sur")

    def test_push_action_enqueues_to_worker_queue(self):
        """Verifica que execute_turn encola las acciones push generadas en worker.task_queue."""
        block = {
            "id": "block_push_test",
            "name": "Push Test",
            "type": "Event",
            "parent_id": None,
            "state": "unknown",
            "active_conditions": [
                {
                    "conditions": [
                        {"entity_type": "place", "entity_id": "p2", "sub_condition": "current_location"}
                    ]
                }
            ],
            "active_effects": [
                {
                    "action": "push",
                    "target": "npc_tom",
                    "directive": "Tom te saluda efusivamente.",
                    "bypass_llm": True,
                }
            ],
            "done_conditions": [],
            "done_effects": [],
        }
        self.controller.game_state.loreblocks.unknown = [block]
        self.controller.game_state.loreblocks.active = []
        self.controller.game_state.loreblocks.done = []

        # Ejecutar MOVE a p2
        res = self.engine.execute_turn(action="MOVE", target="p2")
        self.assertEqual(res.output.author, "Dungeon Master")

        # Comprobar que en worker.task_queue hay una tarea encolada
        self.assertEqual(self.engine.worker.task_queue.qsize(), 1)
        task = self.engine.worker.task_queue.get_nowait()
        self.assertEqual(task.source, "LORE")
        self.assertEqual(task.action, "TALK")
        self.assertEqual(task.target, "npc_tom")
        self.assertEqual(task.directive, "Tom te saluda efusivamente.")
        self.assertTrue(task.bypass_llm)
        self.assertEqual(task.autonomous_depth, 1)


if __name__ == "__main__":
    unittest.main()
