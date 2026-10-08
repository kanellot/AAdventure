from __future__ import annotations

from typing import Dict, List, Optional, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from domains.projections import (
    MapNPCDTO,
    WorldHierarchyProjection,
    WorldMapProjection,
)


class MapTreeWidget(QTreeWidget):
    """
    Árbol de navegación de lugares descubiertos bajo las reglas de niebla de guerra.
    - Muestra los lugares visibles agrupados por localización.
    - Lugares visitados: se marcan como [Visitado] y revelan sus NPCs e ítems contenidos.
    - Lugares visibles (no visitados): se marcan como [Visible] y ocultan sus entidades.
    - El lugar actual del jugador se destaca como [Actual].
    - 1 clic: selecciona la entidad como objetivo en el selector del chat.
    - Doble clic:
      * Lugar distinto al actual -> Ejecuta MOVE hacia ese lugar.
      * Lugar actual -> Ejecuta LOOK sobre el lugar actual.
      * NPC -> Ejecuta TALK con ese NPC.
      * Item -> Ejecuta LOOK sobre ese ítem.
    """

    entity_selected = Signal(str)
    action_requested = Signal(str, str)  # action, target

    def __init__(self, parent=None, header_title: str = "Mapa (Niebla de Guerra)"):
        super().__init__(parent)
        self.setHeaderLabel(header_title)
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
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

    def update_map(self, world_map: Optional[WorldMapProjection], current_place: str = ""):
        """Actualiza el árbol con la proyección del mapa y destaca el lugar actual."""
        expanded_paths = set()
        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            if top.isExpanded():
                expanded_paths.add(top.text(0))
            for j in range(top.childCount()):
                child = top.child(j)
                if child.isExpanded():
                    expanded_paths.add(f"{top.text(0)}/{child.text(0)}")

        self.clear()
        if not world_map:
            return

        bold_font = QFont()
        bold_font.setBold(True)

        for loc in world_map.locations:
            # Filtrar lugares descubiertos (ocultar los que están bajo niebla de guerra con status='hidden')
            discovered_places = [
                p for p in loc.places
                if p.status in ("visited", "visible") or p.id == current_place or p.name == current_place
            ]
            if not discovered_places:
                continue

            loc_item = QTreeWidgetItem(self)
            loc_item.setText(0, loc.name)
            loc_item.setFont(0, bold_font)
            loc_item.setData(0, Qt.UserRole, "location")

            for place in discovered_places:
                p_item = QTreeWidgetItem(loc_item)
                is_current = (place.id == current_place or place.name == current_place)
                is_visited = (place.status == "visited")

                if is_current:
                    label = f"[Actual] {place.name}"
                    fg_color = QColor("#1b5e20")
                    font = QFont()
                    font.setBold(True)
                    p_item.setFont(0, font)
                elif is_visited:
                    label = f"[Visitado] {place.name}"
                    fg_color = QColor("#0d47a1")
                else:
                    label = f"[Visible] {place.name}"
                    fg_color = QColor("#5d4037")

                p_item.setText(0, label)
                p_item.setForeground(0, QBrush(fg_color))
                p_item.setData(0, Qt.UserRole, "place")
                p_item.setData(0, Qt.UserRole + 1, place.name)
                p_item.setData(0, Qt.UserRole + 2, is_current)

                # Contenido solo visible si el lugar fue visitado
                if is_visited and place.entities:
                    for ent in place.entities:
                        ent_item = QTreeWidgetItem(p_item)
                        if isinstance(ent, MapNPCDTO) or hasattr(ent, "status"):
                            ent_item.setText(0, f"[NPC] {ent.name}")
                            ent_item.setForeground(0, QBrush(QColor("#2e7d32")))
                            ent_item.setData(0, Qt.UserRole, "npc")
                            ent_item.setData(0, Qt.UserRole + 1, ent.name)
                        else:
                            ent_item.setText(0, f"[Item] {ent.name}")
                            ent_item.setForeground(0, QBrush(QColor("#e65100")))
                            ent_item.setData(0, Qt.UserRole, "item")
                            ent_item.setData(0, Qt.UserRole + 1, ent.name)

            if not expanded_paths:
                loc_item.setExpanded(True)
            else:
                loc_item.setExpanded(loc_item.text(0) in expanded_paths)

    def update_entities(self, hierarchy=None):
        """Método de retrocompatibilidad."""
        pass

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if not item:
            return
        role = item.data(0, Qt.UserRole)
        name = item.data(0, Qt.UserRole + 1)
        if role in ["place", "npc", "item"] and name:
            self.entity_selected.emit(name)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not item:
            return
        role = item.data(0, Qt.UserRole)
        name = item.data(0, Qt.UserRole + 1)
        if not role or not name:
            return

        is_current = bool(item.data(0, Qt.UserRole + 2))
        if role == "place":
            if is_current:
                self.action_requested.emit("LOOK", name)
            else:
                self.action_requested.emit("MOVE", name)
        elif role == "npc":
            self.action_requested.emit("TALK", name)
        elif role == "item":
            self.action_requested.emit("LOOK", name)


class AllEntitiesTreeWidget(QTreeWidget):
    """
    Árbol exhaustivo de todas las entidades de la historia sin niebla de guerra.
    Utilizado para depuración global (Locations -> Places -> NPCs / Items).
    """

    entity_selected = Signal(str)
    action_requested = Signal(str, str)

    def __init__(self, parent=None, header_title: str = "Todas las Entidades (Debug)"):
        super().__init__(parent)
        self.setHeaderLabel(header_title)
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
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
                color: #3e2b14;
                font-weight: bold;
            }
        """)

    def update_entities(self, hierarchy: Union[WorldHierarchyProjection, List[Dict]]):
        """Puebla el árbol con todas las entidades del mundo."""
        expanded_paths = set()
        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            if top.isExpanded():
                expanded_paths.add(top.text(0))
            for j in range(top.childCount()):
                child = top.child(j)
                if child.isExpanded():
                    expanded_paths.add(f"{top.text(0)}/{child.text(0)}")

        self.clear()
        if not hierarchy:
            return

        bold_font = QFont()
        bold_font.setBold(True)

        location_items = hierarchy.locations if isinstance(hierarchy, WorldHierarchyProjection) else hierarchy

        for loc_data in location_items:
            if isinstance(loc_data, dict):
                loc_name = loc_data.get("location_name", "Localización")
                places = loc_data.get("places", [])
                npcs = loc_data.get("npcs", [])
            else:
                loc_name = loc_data.location_name
                places = loc_data.places
                npcs = loc_data.npcs

            loc_item = QTreeWidgetItem(self)
            loc_item.setText(0, loc_name)
            loc_item.setFont(0, bold_font)
            loc_item.setData(0, Qt.UserRole, "location")

            # Rama Places
            if places:
                p_group = QTreeWidgetItem(loc_item)
                p_group.setText(0, f"Places ({len(places)})")
                p_group.setFont(0, bold_font)
                for p in places:
                    p_name = p.name if hasattr(p, "name") else (p.get("name") if isinstance(p, dict) else str(p))
                    p_item = QTreeWidgetItem(p_group)
                    p_item.setText(0, p_name)
                    p_item.setData(0, Qt.UserRole, "place")
                    p_item.setData(0, Qt.UserRole + 1, p_name)

            # Rama NPCs
            if npcs:
                n_group = QTreeWidgetItem(loc_item)
                n_group.setText(0, f"NPCs ({len(npcs)})")
                n_group.setFont(0, bold_font)
                for n in npcs:
                    n_name = n.name if hasattr(n, "name") else (n.get("name") if isinstance(n, dict) else str(n))
                    n_item = QTreeWidgetItem(n_group)
                    n_item.setText(0, n_name)
                    n_item.setData(0, Qt.UserRole, "npc")
                    n_item.setData(0, Qt.UserRole + 1, n_name)

            if not expanded_paths:
                loc_item.setExpanded(True)
            else:
                loc_item.setExpanded(loc_item.text(0) in expanded_paths)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if not item:
            return
        role = item.data(0, Qt.UserRole)
        name = item.data(0, Qt.UserRole + 1)
        if role in ["place", "npc"] and name:
            self.entity_selected.emit(name)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not item:
            return
        role = item.data(0, Qt.UserRole)
        name = item.data(0, Qt.UserRole + 1)
        if not role or not name:
            return
        if role == "place":
            self.action_requested.emit("LOOK", name)
        elif role == "npc":
            self.action_requested.emit("TALK", name)


# Alias para retrocompatibilidad total con tests existentes
EntitiesTreeWidget = AllEntitiesTreeWidget
