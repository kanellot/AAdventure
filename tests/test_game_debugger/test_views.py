"""Pruebas unitarias para los componentes visuales del depurador (Views)."""

import unittest
from PySide6.QtWidgets import QApplication
from domains import (
    ActionCommand,
    GameStateProjection,
    LoreBlockDetailProjection,
    LoreGraphProjection,
    PlayerSummaryProjection,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnResultProjection,
)
from game_debugger.views.chat_tab import ChatTab
from game_debugger.views.entities_tab import EntitiesTreeWidget
from game_debugger.views.inspector import GameStateInspector
from game_debugger.views.lore_graph_tab import LoreGraphTab
from game_debugger.views.rag_tab import RagTab
from game_debugger.views.result_tab import ResultTab


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
        self.assertIsInstance(cmd, ActionCommand)
        self.assertEqual(cmd.action, "MOVE")
        self.assertEqual(cmd.target, "Calle Pobre")

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

        self.assertGreater(inspector.topLevelItemCount(), 0)
        texts = [inspector.topLevelItem(i).text(0) for i in range(inspector.topLevelItemCount())]
        self.assertTrue(any("player_state: EXPLORE" in t for t in texts))
        self.assertTrue(any("current_place: Plaza Mayor" in t for t in texts))
        self.assertTrue(any("Tiempo Transcurrido" in t for t in texts))

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
            author="Tabernero",
            msg="¡Aquí tienes la jarra más fresca de la comarca!",
            debug_prompt="Prompt enviado al modelo",
            debug_raw_response='{"msg": "¡Aquí tienes..."}',
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
