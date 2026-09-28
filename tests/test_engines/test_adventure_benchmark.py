"""
Suite de Pruebas de Benchmark y Validación Funcional Integral para Adventure.aad.
Ejercita la historia canónica de principio a fin validando:
- Topología de 11 lugares y conectividad.
- Bloqueo y desbloqueo dinámico de salas (p_06 y p_10).
- Catálogo de 8 ítems, transacciones de oro e inventario.
- Interacciones de diálogo y fluctuación de afinidad con NPCs.
- Evaluación semántica RAG (frases antenas).
- Árbol HSM multinivel (Chapter -> Quest -> Task/Event/popup).
- Subcondiciones canónicas (all_children_done, current_location, visited, visible, talk, have, time_range, etc.).
- Eventos popup modales y acciones hook/push.
"""

import os
import unittest
from domains import TurnResultProjection, UIStateProjection
from engines import AdventureSession
from engines.game.engine import GameEngine
from engines.listeners import SyncCollectingEventListener


class TestAdventureBenchmark(unittest.TestCase):
    """Test suite integral de validación de gameplay sobre Adventure.aad."""

    @classmethod
    def setUpClass(cls):
        cls.aad_path = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if not os.path.exists(cls.aad_path):
            raise unittest.SkipTest("Adventure.aad no existe en Resources/adventure_data")

    def setUp(self):
        self.engine = GameEngine(aad_path=self.aad_path)
        self.session = AdventureSession(game_engine=self.engine, aad_path=self.aad_path)
        self.listener = SyncCollectingEventListener()
        self.session.add_listener(self.listener)

    def tearDown(self):
        self.session.close()

    def _get_latest_turn(self) -> TurnResultProjection:
        self.assertGreater(len(self.listener.completed_tasks), 0, "No se completó ninguna tarea en el motor.")
        return TurnResultProjection.model_validate_json(self.listener.completed_tasks[-1][1])

    def _get_latest_ui(self) -> UIStateProjection:
        self.assertGreater(len(self.listener.state_updates), 0, "No hay actualizaciones de estado registradas.")
        return UIStateProjection.model_validate_json(self.listener.state_updates[-1])

    def test_01_initial_state_and_topology(self):
        """Verifica la carga canónica de entidades, lugares bloqueados y niebla de guerra inicial."""
        ctrl = self.engine.game_state_controller
        gs = ctrl.game_state

        # Jugador y Mundo
        self.assertEqual(gs.player_name, "Aventurero")
        self.assertEqual(gs.current_location, "p_00")
        self.assertEqual(gs.gold, 15)
        self.assertEqual(len(gs.inventory.items), 0)

        # 11 Lugares y 8 Ítems
        self.assertEqual(len(ctrl.places_by_id), 11)
        self.assertEqual(len(ctrl.items_by_id), 8)
        self.assertEqual(len(ctrl.npcs_by_id), 9)

        # Salas bloqueadas inicialmente
        self.assertTrue(ctrl.places_by_id["p_06"].blocked_place, "La Sala del Rey (p_06) debe iniciar bloqueada.")
        self.assertTrue(ctrl.places_by_id["p_10"].blocked_place, "El Sótano del Mago (p_10) debe iniciar bloqueado.")

        # Niebla de guerra en p_00: p_00 es visited, sus 4 colindantes visibles, el resto hidden
        places_status = {p.id: p.status for loc in gs.entity_map for p in loc.places}
        self.assertEqual(places_status["p_00"], "visited")
        self.assertEqual(places_status["p_01"], "visible")
        self.assertEqual(places_status["p_07"], "visible")
        self.assertEqual(places_status["p_08"], "visible")
        self.assertEqual(places_status["p_09"], "visible")
        self.assertEqual(places_status["p_06"], "hidden")
        self.assertEqual(places_status["p_10"], "hidden")

        # HSM Inicial: Capítulo 1 activo
        active_ids = {b["id"] for b in gs.loreblocks.active}
        self.assertIn("c1_villa_roca", active_ids)
        self.assertIn("q_favor_mendigo", active_ids)
        self.assertIn("q_secreto_mago", active_ids)
        self.assertIn("q_salvoconducto", active_ids)

    def test_02_blocked_place_obstacle_rejection(self):
        """El intento de cruzar a una sala bloqueada (p_06 o p_10) debe ser rechazado por PathCalculator."""
        # 1. Desplazarse hacia la Entrada al Castillo
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Entrada al Castillo")
        self.session.wait_idle()

        # Intentar entrar en la Sala del Rey (bloqueada inicialmente)
        self.session.post_action("MOVE", "Sala del Rey")
        self.session.wait_idle()

        res = self._get_latest_turn()
        ui = self._get_latest_ui()
        # Debe permanecer en la Entrada al Castillo y describir el obstáculo
        self.assertEqual(ui.current_location, "Entrada al Castillo")
        self.assertIn("bloquead", res.output.msg.lower())

    def test_03_shop_transaction_and_inventory_condition(self):
        """Prueba compra en tienda: deducción de oro, ganancia de ítems y finalización de Quest."""
        ctrl = self.engine.game_state_controller

        # Mover a Plaza Menor y luego Tienda
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Tienda")
        self.session.wait_idle()

        # Al entrar con 15 de oro, se activa y completa t_comprar_salvoconducto
        res = self._get_latest_turn()
        ui = self._get_latest_ui()
        self.assertEqual(ui.current_location, "Tienda")

        # Oro debe haberse reducido en 10 (15 - 10 = 5)
        self.assertEqual(ctrl.game_state.gold, 5)
        # Debe tener salvoconducto y pan
        self.assertIn("item_salvoconducto", ctrl.game_state.inventory.items)
        self.assertIn("item_pan", ctrl.game_state.inventory.items)

        # q_salvoconducto debe haber pasado a done
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("q_salvoconducto", done_ids)

    def test_04_rag_event_under_table_in_tavern(self):
        """Prueba de activación semántica RAG en la taberna mediante frase disparadora."""
        ctrl = self.engine.game_state_controller

        # Mover a Plaza Menor -> Taberna
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Taberna")
        self.session.wait_idle()

        # Iniciar diálogo o texto libre con frase disparadora RAG
        self.session.post_action("TALK", "npc_tabernero")
        self.session.wait_idle()

        # Enviar mensaje que active la antena RAG "mirar bajo la mesa"
        self.session.post_action(action="", target="", player_input="Voy a mirar bajo la mesa para ver si hay algo escondido.")
        self.session.wait_idle()

        # ev_taberna_secreto debe completarse y otorgar item_llave_bodega
        self.assertIn("item_llave_bodega", ctrl.game_state.inventory.items)
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("ev_taberna_secreto", done_ids)

    def test_05_complete_walkthrough_benchmark(self):
        """Walkthrough completo de extremo a extremo cubriendo todos los mecanismos."""
        ctrl = self.engine.game_state_controller

        # --- Paso 1: Tienda (Comprar provisiones y salvoconducto) ---
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Tienda")
        self.session.wait_idle()

        self.assertIn("item_pan", ctrl.game_state.inventory.items)
        self.assertIn("item_salvoconducto", ctrl.game_state.inventory.items)

        # --- Paso 1.5: Taberna (Secreto bajo la mesa mediante RAG) ---
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Taberna")
        self.session.wait_idle()
        self.session.post_action("TALK", "npc_tabernero")
        self.session.wait_idle()
        self.session.post_action(action="", target="", player_input="Voy a mirar bajo la mesa para ver si hay algo escondido.")
        self.session.wait_idle()
        self.assertIn("item_llave_bodega", ctrl.game_state.inventory.items)

        # --- Paso 2: Mendigo (Hablar y entregar pan con RAG) ---
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()

        # Hablar con el mendigo -> completa t_hablar_mendigo
        self.session.post_action("TALK", "npc_mendigo")
        self.session.wait_idle()
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("t_hablar_mendigo", done_ids)

        # Dar pan al mendigo usando texto libre -> completa t_dar_pan_mendigo
        self.session.post_action(action="", target="", player_input="Aquí tienes pan, buen hombre, toma este trozo de pan caliente.")
        self.session.wait_idle()

        # Pan retirado, moneda entregada, afinidad incrementada
        self.assertNotIn("item_pan", ctrl.game_state.inventory.items)
        self.assertIn("item_moneda_antigua", ctrl.game_state.inventory.items)
        self.assertGreaterEqual(ctrl.get_npc_affinity("npc_mendigo"), 0.8)

        # q_favor_mendigo completada
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("q_favor_mendigo", done_ids)

        # --- Paso 3: Iglesia (Bendición temporal y de visita) ---
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Iglesia")
        self.session.wait_idle()

        self.session.post_action("TALK", "npc_cura")
        self.session.wait_idle()
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("ev_iglesia_bendicion", done_ids)

        # --- Paso 4: Parque (Visibilidad de niños) ---
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Parque")
        self.session.wait_idle()
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("ev_parque_juegos", done_ids)

        # --- Paso 5: Casa del Mago y Sótano Secreto ---
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Casa Mago")
        self.session.wait_idle()

        # Recoger Llave Arcana y desbloquear trampilla
        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("t_llave_arcana", done_ids)
        self.assertIn("t_abrir_sotano", done_ids)

        # Verificar que el Sótano (p_10) se ha desbloqueado dinámicamente
        self.assertFalse(ctrl.places_by_id["p_10"].blocked_place, "El sótano debe estar desbloqueado tras usar la llave.")

        # Descender al Sótano del Mago y recoger el Grimorio
        self.session.post_action("MOVE", "Sótano del Mago")
        self.session.wait_idle()
        self.assertIn("item_grimorio_antiguo", ctrl.game_state.inventory.items)

        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("q_secreto_mago", done_ids)

        # --- Paso 6: Cascada HSM (Capítulo 1 pasa a done -> Capítulo 2 se activa) ---
        self.assertIn("c1_villa_roca", done_ids, "El Capítulo 1 debe estar concluido al finalizar todas sus misiones.")

        active_ids = {b["id"] for b in ctrl.game_state.loreblocks.active}
        self.assertIn("c2_el_castillo", active_ids, "El Capítulo 2 debe activarse tras completar el Capítulo 1.")
        self.assertFalse(ctrl.places_by_id["p_06"].blocked_place, "La Sala del Rey debe desbloquearse en el Capítulo 2.")

        # --- Paso 7: Entrada al Castillo y Audiencia Real con el Rey Arturo ---
        self.session.post_action("MOVE", "Casa Mago")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Mayor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Calle Pobre")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Plaza Menor")
        self.session.wait_idle()
        self.session.post_action("MOVE", "Entrada al Castillo")
        self.session.wait_idle()

        # Entrar a la Sala del Rey (ahora desbloqueada)
        self.session.post_action("MOVE", "Sala del Rey")
        self.session.wait_idle()

        ui = self._get_latest_ui()
        self.assertEqual(ui.current_location, "Sala del Rey")

        # Conversar con el Rey Arturo para presentar el Grimorio
        self.session.post_action("TALK", "npc_rey_arturo")
        self.session.wait_idle()

        # Recompensa real: +100 oro, grimorio entregado y popup de victoria
        self.assertEqual(ctrl.game_state.gold, 105)
        self.assertNotIn("item_grimorio_antiguo", ctrl.game_state.inventory.items)

        done_ids = {b["id"] for b in ctrl.game_state.loreblocks.done}
        self.assertIn("q_audiencia_real", done_ids)

        res_final = self._get_latest_turn()
        self.assertTrue(
            res_final.output.type == "popup" or res_final.output.popup_message is not None,
            "Debe emitirse un popup de felicitación/victoria final.",
        )

    def test_06_monkey_island_passive_hook_injection(self):
        """Verifica que un bloque en estado active con action 'hook' inyecta continuamente su directriz en diálogos con el NPC."""
        ctrl = self.engine.game_state_controller

        # Simulamos un bloque de tarea activo al estilo Monkey Island:
        # El tabernero insiste continuamente en que necesita que encuentres la cerveza
        ctrl.game_state.loreblocks.active.append({
            "id": "t_monkey_island_guide",
            "name": "Guía continua del tabernero",
            "state": "active",
            "done_conditions": [
                {
                    "conditions": [
                        {"entity_type": "item", "entity_id": "item_cerveza", "sub_condition": "have"}
                    ]
                }
            ],
            "effects": [
                {
                    "target": "npc_tabernero",
                    "action": "hook",
                    "directive": "Insiste en que necesitas encontrar una jarra de cerveza para refrescar el gaznate.",
                }
            ],
        })

        # Moverse a la Taberna (p_03)
        self.session.post_action("MOVE", "Taberna")
        self.session.wait_idle()

        # Hablar con el tabernero con un saludo genérico ("Hola buen hombre") sin antena RAG específica
        self.session.post_action("TALK", "npc_tabernero", player_input="Hola buen hombre")
        self.session.wait_idle()

        latest_turn = self._get_latest_turn()
        self.assertIsNotNone(latest_turn.debug.prompt, "El prompt de depuración debe estar disponible.")
        self.assertIn(
            "Insiste en que necesitas encontrar una jarra de cerveza para refrescar el gaznate",
            latest_turn.debug.prompt,
            "El prompt enviado al LLM debe contener la directriz del hook activo (estilo Monkey Island).",
        )


if __name__ == "__main__":
    unittest.main()

