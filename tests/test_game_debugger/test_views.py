"""Pruebas unitarias para los componentes visuales del depurador (Views)."""

import unittest

from PySide6.QtWidgets import QApplication

from domains.projections import (
    ActionCommandProjection,
    GameStateProjection,
    InventoryProjection,
    LoreBlockDetailProjection,
    LoreGraphProjection,
    NotebookProjection,
    PlayerSummaryProjection,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnDebugProjection,
    TurnOutput,
    TurnResultProjection,
    WorldMapProjection,
)
from editor_debugger.debugger.views.chat_tab import ChatTab
from editor_debugger.debugger.views.entities_tab import EntitiesTreeWidget
from editor_debugger.debugger.views.inspector import GameStateInspector
from editor_debugger.debugger.views.lore_graph_tab import LoreGraphTab
from editor_debugger.debugger.views.rag_tab import RagTab
from editor_debugger.debugger.views.result_tab import ResultTab


class TestDebuggerViews(unittest.TestCase):
    """Verifica el comportamiento interactivo y renderizado de las pestañas del depurador."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def test_chat_tab_interactions(self):
        chat = ChatTab()
        chat.set_targets(["Plaza Mayor", "Calle Pobre", "Tabernero"])
        self.assertEqual(chat.target_combo.count(), 3)

        # Estado TALK
        chat.set_game_state("TALK", active_affinity=0.85, target_name="Tabernero")
        self.assertFalse(chat.send_btn.isHidden())
        self.assertFalse(chat.lbl_affinity.isHidden())
        self.assertIn("0.85", chat.lbl_affinity.text())

        # Estado EXPLORE
        chat.set_game_state("EXPLORE")
        self.assertTrue(chat.send_btn.isHidden())
        self.assertTrue(chat.lbl_affinity.isHidden())

        # Añadir mensaje
        chat.append_message("Dungeon Master", "Avanzas hacia la plaza.")
        html = chat.chat_browser.toHtml()
        self.assertIn("Dungeon Master", html)
        self.assertIn("Avanzas hacia la plaza.", html)

        # Disparo de acción directa
        emitted_actions = []
        chat.send_action.connect(lambda cmd, inp: emitted_actions.append((cmd, inp)))
        chat.target_combo.setCurrentText("Calle Pobre")
        chat.on_action_btn_clicked("MOVE")

        self.assertEqual(len(emitted_actions), 1)
        cmd, player_inp = emitted_actions[0]
        self.assertIsInstance(cmd, ActionCommandProjection)
        self.assertEqual(cmd.action, "MOVE")
        self.assertEqual(cmd.target, "Calle Pobre")

    def test_chat_tab_set_thinking(self):
        chat = ChatTab()
        chat.set_game_state("TALK")
        self.assertTrue(chat.spinner.isHidden())
        self.assertTrue(chat.lbl_thinking.isHidden())

        # Activar Thinking
        chat.set_thinking(True, "Consultando al DM...")
        self.assertFalse(chat.spinner.isHidden())
        self.assertFalse(chat.lbl_thinking.isHidden())
        self.assertIn("Consultando al DM...", chat.lbl_thinking.text())
        self.assertFalse(chat.input_edit.isEnabled())
        self.assertFalse(chat.send_btn.isEnabled())

        # Desactivar Thinking
        chat.set_thinking(False)
        self.assertTrue(chat.spinner.isHidden())
        self.assertTrue(chat.lbl_thinking.isHidden())
        self.assertTrue(chat.input_edit.isEnabled())
        self.assertTrue(chat.send_btn.isEnabled())

    def test_entities_tree_widget(self):
        tree = EntitiesTreeWidget(header_title="Test Entidades")
        hierarchy = [
            {
                "location_name": "Villa Roca",
                "places": ["Plaza Mayor", "Taberna"],
                "npcs": ["Tabernero"],
            }
        ]
        tree.update_entities(hierarchy)

        self.assertEqual(tree.topLevelItemCount(), 1)
        top_item = tree.topLevelItem(0)
        self.assertEqual(top_item.text(0), "Villa Roca")
        # El nodo de localización tiene 2 subnodos categoría: Places (2) y NPCs (1)
        self.assertEqual(top_item.childCount(), 2)
        places_node = top_item.child(0)
        self.assertEqual(places_node.childCount(), 2)

        emitted_entities = []
        tree.entity_selected.connect(emitted_entities.append)
        tree._on_item_clicked(places_node.child(0), 0)
        self.assertEqual(len(emitted_entities), 1)
        self.assertEqual(emitted_entities[0], "Plaza Mayor")

    def test_game_state_inspector(self):
        inspector = GameStateInspector()
        dto = GameStateProjection(
            player=PlayerSummaryProjection(id="player", name="Aventurero", gold=42),
            player_state="EXPLORE",
            current_place="Plaza Mayor",
            travel_speed=4.5,
            formatted_time="Día 1, 08:30",
            elapsed_time=150,
        )
        inspector.update_state(dto)

        self.assertEqual(inspector.columnCount(), 2)
        self.assertGreater(inspector.topLevelItemCount(), 0)

        # Buscar propiedades en la jerarquía de 2 columnas
        found_props = {}
        for i in range(inspector.topLevelItemCount()):
            top = inspector.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                found_props[child.text(0)] = child.text(1)

        self.assertEqual(found_props.get("player_state"), "EXPLORE")
        self.assertEqual(found_props.get("current_place"), "Plaza Mayor")
        self.assertEqual(found_props.get("formatted_time"), "Día 1, 08:30")

    def test_notebook_tree_widget(self):
        from editor_debugger.debugger.views.inspector import NotebookTreeWidget
        from domains.game_state import NotebookEntry
        nb_tree = NotebookTreeWidget()
        projection = NotebookProjection(
            quests=[
                NotebookEntry(id="q1", name="Misión Activa", description="Detalle activo", status="active"),
                NotebookEntry(id="q2", name="Misión Completada", description="Detalle hecho", status="done"),
            ]
        )
        nb_tree.update_notebook(projection)
        self.assertEqual(nb_tree.topLevelItemCount(), 2)
        self.assertIn("Activas (1)", nb_tree.topLevelItem(0).text(0))
        self.assertIn("Completadas (1)", nb_tree.topLevelItem(1).text(0))

    def test_map_tree_widget(self):
        from editor_debugger.debugger.views.entities_tab import MapTreeWidget
        from domains.projections import MapLocationDTO, MapPlaceDTO, MapNPCDTO
        map_tree = MapTreeWidget()
        world_map = WorldMapProjection(
            locations=[
                MapLocationDTO(
                    id="loc_1",
                    name="Valle",
                    places=[
                        MapPlaceDTO(
                            id="p_1",
                            name="Plaza Mayor",
                            status="visited",
                            entities=[MapNPCDTO(id="n_1", name="Tabernero")],
                        ),
                        MapPlaceDTO(
                            id="p_2",
                            name="Bosque",
                            status="visible",
                            entities=[],
                        ),
                        MapPlaceDTO(
                            id="p_3",
                            name="Cueva Oculta",
                            status="hidden",
                            entities=[],
                        ),
                    ],
                ),
                MapLocationDTO(
                    id="loc_2",
                    name="Reino Lejano",
                    places=[
                        MapPlaceDTO(
                            id="p_4",
                            name="Castillo Oculto",
                            status="hidden",
                            entities=[],
                        ),
                    ],
                ),
            ]
        )
        map_tree.update_map(world_map, current_place="Plaza Mayor")
        # loc_2 solo tiene lugares ocultos, no debe incluirse
        self.assertEqual(map_tree.topLevelItemCount(), 1)
        loc_item = map_tree.topLevelItem(0)
        # Solo p_1 (visitado/actual) y p_2 (visible) deben incluirse; p_3 (hidden) queda excluido
        self.assertEqual(loc_item.childCount(), 2)

        p1_item = loc_item.child(0)
        self.assertIn("[Actual]", p1_item.text(0))
        p2_item = loc_item.child(1)
        self.assertIn("[Visible]", p2_item.text(0))
        # Al estar visitado, muestra el NPC como hijo
        self.assertEqual(p1_item.childCount(), 1)
        self.assertIn("[NPC] Tabernero", p1_item.child(0).text(0))

        # Doble clic en NPC emite TALK
        emitted_actions = []
        map_tree.action_requested.connect(lambda a, t: emitted_actions.append((a, t)))
        map_tree._on_item_double_clicked(p1_item.child(0), 0)
        self.assertEqual(emitted_actions, [("TALK", "Tabernero")])

    def test_chat_tab_header_info(self):
        chat = ChatTab()
        chat.update_header_info("Día 2, 14:00", "TALK", "Taberna")
        self.assertEqual(chat.header_time_lbl.text(), "[Tiempo: Día 2, 14:00]")
        self.assertEqual(chat.header_state_lbl.text(), "[Estado: TALK]")
        self.assertEqual(chat.header_loc_lbl.text(), "[Ubicación: Taberna]")

    def test_lore_graph_tab(self):
        lore_tab = LoreGraphTab()
        projection = LoreGraphProjection(
            blocks=[
                LoreBlockDetailProjection(
                    id="lb_01",
                    name="Misión 1",
                    title="Misión 1",
                    state="active",
                    is_accessible=True,
                )
            ],
            total_count=1,
            active_count=1,
            done_count=0,
            unknown_count=0,
        )
        lore_tab.update_lore_graph(projection)

        self.assertEqual(lore_tab.lbl_total.text(), "Total: 1")
        self.assertEqual(lore_tab.lbl_active.text(), "🟢 Activos: 1")
        self.assertEqual(lore_tab.lbl_done.text(), "🔵 Completados: 0")
        self.assertEqual(lore_tab.lbl_unknown.text(), "🟡 Pendientes: 0")

    def test_rag_tab(self):
        rag_tab = RagTab()
        rag_eval = RagEvaluationProjection(
            player_input="dame una cerveza",
            threshold=0.65,
            matched_lore_id="lb_01",
            matched_antenna="cerveza fria",
            injected_directive="El tabernero sirve sidra.",
            antennas=[
                RagAntennaScoreProjection(
                    antenna="cerveza fria",
                    lore_id="lb_01",
                    lore_title="Taberna",
                    score=0.88,
                    is_matched=True,
                )
            ],
        )
        rag_tab.update_rag_evaluation(rag_eval)

        self.assertEqual(rag_tab.player_input_edit.text(), "dame una cerveza")
        self.assertIn("COINCIDENCIA", rag_tab.status_badge.text())
        self.assertIn("cerveza fria", rag_tab.browser.toHtml())
        self.assertIn("El tabernero sirve sidra.", rag_tab.directive_edit.text())

    def test_result_tab(self):
        result_tab = ResultTab()
        turn_res = TurnResultProjection(
            output=TurnOutput(
                author="Tabernero",
                msg="¡Aquí tienes la jarra más fresca de la comarca!",
            ),
            map=WorldMapProjection(),
            inventory=InventoryProjection(),
            notebook=NotebookProjection(),
            debug=TurnDebugProjection(
                prompt="Prompt enviado al modelo",
                raw_response='{"msg": "¡Aquí tienes..."}',
            ),
        )
        result_tab.update_result(turn_res)

        self.assertEqual(result_tab.author_label.text(), "Autor: Tabernero")
        self.assertEqual(
            result_tab.narrative_edit.toPlainText(),
            "¡Aquí tienes la jarra más fresca de la comarca!",
        )
        self.assertIn('{"msg": "¡Aquí tienes..."}', result_tab.raw_response_edit.toPlainText())


if __name__ == "__main__":
    unittest.main()
