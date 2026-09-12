from typing import List, Dict
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

class EntitiesTreeWidget(QTreeWidget):
    """
    Árbol jerárquico de entidades del mundo.
    Organiza las localizaciones con sus lugares (solo nombre) y sus NPCs (solo nombre).
    Permite colapsar/expandir ramas y emite una señal al seleccionar un lugar o NPC.
    """
    entity_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Árbol de Entidades")
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)
        self.currentItemChanged.connect(self._on_current_item_changed)

    def update_entities(self, hierarchy: List[Dict]):
        """
        Puebla el árbol con las localizaciones, lugares y NPCs.
        """
        # Guardar estado de expansión si ya había elementos
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

        for loc_data in hierarchy:
            loc_name = loc_data.get("location_name", "Localización")
            loc_item = QTreeWidgetItem(self)
            loc_item.setText(0, loc_name)
            loc_item.setFont(0, bold_font)
            loc_item.setData(0, Qt.UserRole, "location")

            # Rama de Places
            places = loc_data.get("places", [])
            places_node = QTreeWidgetItem(loc_item)
            places_node.setText(0, f"Places ({len(places)})")
            places_node.setFont(0, bold_font)
            places_node.setData(0, Qt.UserRole, "category_places")

            visited_in_loc = loc_data.get("visited_places", [])
            visible_in_loc = loc_data.get("visible_places", [])

            for place_entry in places:
                p_item = QTreeWidgetItem(places_node)

                if isinstance(place_entry, dict):
                    place_name = place_entry.get("name", "")
                    status = place_entry.get("status", "visible")
                else:
                    place_name = str(place_entry)
                    status = getattr(place_entry, "status", None)
                    if not status:
                        if place_name in visited_in_loc:
                            status = "visited"
                        elif place_name in visible_in_loc:
                            status = "visible"
                        else:
                            status = "visible"

                p_item.setText(0, place_name)
                p_item.setData(0, Qt.UserRole, "place")
                p_item.setData(0, Qt.UserRole + 1, status)

                if status == "visited":
                    # Lugar visitado: con las letras azules
                    p_item.setForeground(0, QBrush(QColor("#1565C0")))
                    p_item.setToolTip(0, f"{place_name} (Lugar visitado)")
                elif status == "visible":
                    # Lugar visible: colindante no visitado (color normal)
                    p_item.setForeground(0, QBrush(QColor("#3e2b14")))
                    p_item.setToolTip(0, f"{place_name} (Lugar visible - no visitado)")

            # Rama de NPCs
            npcs = loc_data.get("npcs", [])
            npcs_node = QTreeWidgetItem(loc_item)
            npcs_node.setText(0, f"NPCs ({len(npcs)})")
            npcs_node.setFont(0, bold_font)
            npcs_node.setData(0, Qt.UserRole, "category_npcs")

            for npc_name in npcs:
                n_item = QTreeWidgetItem(npcs_node)
                n_item.setText(0, npc_name)
                n_item.setData(0, Qt.UserRole, "npc")

            # Restaurar o expandir por defecto
            if not expanded_paths:
                loc_item.setExpanded(True)
                places_node.setExpanded(True)
                npcs_node.setExpanded(True)
            else:
                loc_item.setExpanded(loc_name in expanded_paths)
                places_node.setExpanded(f"{loc_name}/{places_node.text(0)}" in expanded_paths)
                npcs_node.setExpanded(f"{loc_name}/{npcs_node.text(0)}" in expanded_paths)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if not item:
            return
        role = item.data(0, Qt.UserRole)
        if role in ["place", "npc"]:
            self.entity_selected.emit(item.text(0))

    def _on_current_item_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if not current:
            return
        role = current.data(0, Qt.UserRole)
        if role in ["place", "npc"]:
            self.entity_selected.emit(current.text(0))
