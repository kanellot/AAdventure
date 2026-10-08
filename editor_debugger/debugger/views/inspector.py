from __future__ import annotations

from typing import Optional, Union, List

from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from domains.game_state import NotebookEntry
from domains.projections import GameStateProjection, NotebookProjection


class NotebookTreeWidget(QTreeWidget):
    """
    Visor jerárquico del cuaderno de misiones del juego (Notebook).
    Organiza las misiones en dos categorías claras: Activas y Completadas,
    mostrando el nombre y la descripción detallada de cada misión.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Cuaderno de Misiones (Notebook)")
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #faf6df;
                color: #2b2b2b;
                border: 1px solid #d5c796;
                border-radius: 4px;
                padding: 4px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #d7ccc8;
                color: #3e2723;
                font-weight: bold;
            }
        """)

    def update_notebook(self, notebook_data: Optional[Union[NotebookProjection, List[NotebookEntry]]]):
        """Actualiza el árbol con las misiones activas y completadas."""
        self.clear()
        if not notebook_data:
            return

        quests = notebook_data.quests if isinstance(notebook_data, NotebookProjection) else notebook_data
        active_quests = [q for q in quests if getattr(q, "status", "active") == "active"]
        done_quests = [q for q in quests if getattr(q, "status", "active") == "done"]

        bold_font = QFont()
        bold_font.setBold(True)

        # Categoría: Misiones Activas
        act_header = QTreeWidgetItem(self)
        act_header.setText(0, f"🟡 Misiones Activas ({len(active_quests)})")
        act_header.setFont(0, bold_font)
        act_header.setForeground(0, QBrush(QColor("#e65100")))

        for q in active_quests:
            q_item = QTreeWidgetItem(act_header)
            q_name = getattr(q, "name", "Misión sin nombre")
            q_item.setText(0, f"⚔️ {q_name}")
            q_item.setFont(0, bold_font)
            q_item.setForeground(0, QBrush(QColor("#3e2723")))

            q_desc = getattr(q, "description", "")
            if q_desc:
                desc_item = QTreeWidgetItem(q_item)
                desc_item.setText(0, f"📄 {q_desc}")
                desc_item.setForeground(0, QBrush(QColor("#5d4037")))

        # Categoría: Misiones Completadas
        done_header = QTreeWidgetItem(self)
        done_header.setText(0, f"🔵 Misiones Completadas ({len(done_quests)})")
        done_header.setFont(0, bold_font)
        done_header.setForeground(0, QBrush(QColor("#0d47a1")))

        for q in done_quests:
            q_item = QTreeWidgetItem(done_header)
            q_name = getattr(q, "name", "Misión sin nombre")
            q_item.setText(0, f"✓ {q_name}")
            q_item.setFont(0, bold_font)
            q_item.setForeground(0, QBrush(QColor("#1b5e20")))

            q_desc = getattr(q, "description", "")
            if q_desc:
                desc_item = QTreeWidgetItem(q_item)
                desc_item.setText(0, f"📄 {q_desc}")
                desc_item.setForeground(0, QBrush(QColor("#616161")))

        self.expandAll()


class GameStateHierarchicalTreeWidget(QTreeWidget):
    """
    Inspector interactivo del GameState completo en 2 columnas:
    Columna 0: Propiedad | Columna 1: Valor.
    Expone Player, Runtime State, Current Place, Percepción y LoreBlocks (HSM).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Propiedad", "Valor"])
        self.setColumnCount(2)
        self.setAlternatingRowColors(True)
        self.setColumnWidth(0, 190)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #faf6df;
                color: #2b2b2b;
                border: 1px solid #d5c796;
                border-radius: 4px;
                padding: 4px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #d7ccc8;
                color: #3e2723;
                font-weight: bold;
            }
        """)

    def update_state(self, game_state: Optional[GameStateProjection]) -> None:
        """Limpia y reconstruye el árbol con la información en dos columnas del GameStateProjection."""
        self.clear()
        if not game_state:
            return

        bold_font = QFont()
        bold_font.setBold(True)

        def add_prop(parent_item, key: str, val: str, is_bold: bool = False) -> QTreeWidgetItem:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, key)
            item.setText(1, str(val))
            if is_bold:
                item.setFont(0, bold_font)
                item.setFont(1, bold_font)
            return item

        # 1. SECCIÓN: Runtime State
        sec_runtime = QTreeWidgetItem(self)
        sec_runtime.setText(0, "⚙️ Runtime State")
        sec_runtime.setFont(0, bold_font)

        add_prop(sec_runtime, "player_state", game_state.player_state, is_bold=True)
        add_prop(sec_runtime, "player_target", game_state.player_target or "(ninguno)")

        if game_state.player_state.upper() == "TALK" and game_state.active_npc_affinity is not None:
            pct = int(round(game_state.active_npc_affinity * 100))
            add_prop(sec_runtime, "active_affinity", f"{game_state.active_npc_affinity:.2f} ({pct}%)")

        add_prop(sec_runtime, "current_place", game_state.current_place or "(ninguno)")
        add_prop(sec_runtime, "prev_place", game_state.prev_place or "(ninguno)")
        add_prop(sec_runtime, "travel_speed", f"{game_state.travel_speed} km/h")
        add_prop(sec_runtime, "elapsed_time", f"{game_state.elapsed_time} min")
        add_prop(sec_runtime, "formatted_time", game_state.formatted_time)

        # 2. SECCIÓN: Jugador (Player)
        player = game_state.player
        if player:
            sec_player = QTreeWidgetItem(self)
            sec_player.setText(0, f"👤 Jugador ({player.name})")
            sec_player.setFont(0, bold_font)

            add_prop(sec_player, "id", player.id)
            add_prop(sec_player, "name", player.name)
            add_prop(sec_player, "description", player.description)
            add_prop(sec_player, "gold", f"{player.gold} monedas")
            add_prop(sec_player, "active_quest", player.active_quest or "(ninguna)")
            add_prop(sec_player, "completed_quests", f"{len(player.completed_quests)} misiones")

            inv_node = add_prop(sec_player, "inventory", f"({len(player.inventory)} ítems)")
            for it in player.inventory:
                add_prop(inv_node, "• ítem", it)

            add_prop(sec_player, "visited_places", f"{len(player.visited_places)} lugares")

        # 3. SECCIÓN: Lugar Actual (Place Detail)
        curr_detail = game_state.current_place_detail
        if curr_detail:
            sec_place = QTreeWidgetItem(self)
            sec_place.setText(0, f"📍 Lugar Actual ({curr_detail.name})")
            sec_place.setFont(0, bold_font)

            add_prop(sec_place, "id", curr_detail.id)
            add_prop(sec_place, "name", curr_detail.name)
            add_prop(sec_place, "description", curr_detail.description)

            ents_node = add_prop(sec_place, "visible_entities", f"({len(curr_detail.visible_entities)})")
            for ent in curr_detail.visible_entities:
                add_prop(ents_node, "• entidad", ent)

            if curr_detail.connections:
                conn_node = add_prop(sec_place, "connections", f"({len(curr_detail.connections)} salidas)")
                for conn in curr_detail.connections:
                    add_prop(conn_node, f"[{conn.direction}]", f"-> {conn.target} ({conn.distance}m)")

        # 4. SECCIÓN: Percepción (Fog of War)
        sec_fog = QTreeWidgetItem(self)
        sec_fog.setText(0, "🌫️ Percepción (Fog of War)")
        sec_fog.setFont(0, bold_font)

        add_prop(sec_fog, "discovered_places", f"{len(game_state.discovered_places)} lugares")
        add_prop(sec_fog, "visible_npcs", f"{len(game_state.visible_npcs)} NPCs")

        # 5. SECCIÓN: LoreBlocks (HSM)
        if game_state.active_lore_blocks or game_state.done_lore_blocks:
            sec_lore = QTreeWidgetItem(self)
            sec_lore.setText(0, "📜 LoreBlocks (HSM)")
            sec_lore.setFont(0, bold_font)

            act_lore_node = add_prop(sec_lore, "Activos", f"({len(game_state.active_lore_blocks)})")
            for blk_id in game_state.active_lore_blocks:
                add_prop(act_lore_node, "•", blk_id)

            done_lore_node = add_prop(sec_lore, "Completados", f"({len(game_state.done_lore_blocks)})")
            for blk_id in game_state.done_lore_blocks:
                add_prop(done_lore_node, "•", blk_id)

        self.expandAll()


# Alias para compatibilidad total
GameStateInspector = GameStateHierarchicalTreeWidget
