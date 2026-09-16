"""Formulario de Lugar (Place) organizado por pestañas:
1. Pestaña General: Propiedades y Entidades Visibles (NPCs y Objetos locales).
2. Pestaña Conexiones: Conexiones de viaje limpias hacia lugares colindantes (sin tablas rígidas).
3. Pestaña LoreBlocks: Referencias cruzadas a LoreBlocks directos o indirectos (vía NPCs u Objetos).
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QPushButton, QGroupBox, QTabWidget,
    QScrollArea, QFrame, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from domains import Place, NPC, Item
from editor.views.dialogs import ConnectionDialog
from editor.views.compact_widgets import CompactEntityListWidget, LoreReferenceListWidget


class PlaceForm(QWidget):
    """Formulario moderno y modular para la edición integral de un Lugar (Place)."""

    lore_block_requested = Signal(str)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.parent_app = parent
        self.place: Optional[Place] = None
        self.all_places: List[Place] = []
        self.all_npcs: List[NPC] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con botón de eliminar
        top_bar = QHBoxLayout()
        self.header_title = QLabel("<b>📍 Lugar</b>")
        self.header_title.setStyleSheet("font-size: 14px; color: #005a9e;")
        top_bar.addWidget(self.header_title)
        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar este lugar del mundo")
        self.del_btn.setStyleSheet("""
            QPushButton {
                color: #cc0000;
                font-size: 11px;
                padding: 3px 8px;
                border: 1px solid #ffcccc;
                border-radius: 3px;
                background: #fff5f5;
            }
            QPushButton:hover {
                background: #ffe6e6;
                border-color: #cc0000;
            }
        """)
        self.del_btn.clicked.connect(self.on_delete_clicked)
        top_bar.addWidget(self.del_btn)
        main_layout.addLayout(top_bar)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # =====================================================================
        # PESTAÑA 1: General (Propiedades y Entidades Visibles)
        # =====================================================================
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)

        props_group = QGroupBox("Propiedades del Lugar")
        props_form = QFormLayout(props_group)

        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        props_form.addRow("ID del Lugar:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del lugar...")
        self.name_edit.textChanged.connect(self.on_name_changed)
        props_form.addRow("Nombre:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Descripción ambiental del lugar...")
        self.desc_edit.setMaximumHeight(90)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        props_form.addRow("Descripción:", self.desc_edit)

        gen_layout.addWidget(props_group)

        # Entidades Visibles (NPCs u Objetos)
        vis_group = QGroupBox("Entidades Visibles (Personajes y Objetos presentes)")
        vis_layout = QVBoxLayout(vis_group)
        self.visible_entities_widget = CompactEntityListWidget(
            controller=self.controller,
            allowed_types=["npc", "item"],
            button_text="➕ Añadir Entidad Visible...",
            parent=self
        )
        self.visible_entities_widget.entities_changed.connect(self.on_visible_entities_changed)
        vis_layout.addWidget(self.visible_entities_widget)
        gen_layout.addWidget(vis_group)

        self.tab_widget.addTab(self.tab_general, "General")

        # =====================================================================
        # PESTAÑA 2: Conexiones de Viaje
        # =====================================================================
        self.tab_connections = QWidget()
        conn_layout = QVBoxLayout(self.tab_connections)

        top_conn_bar = QHBoxLayout()
        self.add_conn_btn = QPushButton("➕ Añadir Conexión...")
        self.add_conn_btn.setStyleSheet("padding: 4px 10px; font-weight: bold;")
        self.add_conn_btn.clicked.connect(self.on_add_connection)
        top_conn_bar.addWidget(self.add_conn_btn)
        top_conn_bar.addStretch()
        conn_layout.addLayout(top_conn_bar)

        self.conn_scroll = QScrollArea()
        self.conn_scroll.setWidgetResizable(True)
        self.conn_scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")

        self.conn_container = QWidget()
        self.conn_container_layout = QVBoxLayout(self.conn_container)
        self.conn_container_layout.setContentsMargins(6, 6, 6, 6)
        self.conn_container_layout.setSpacing(6)
        self.conn_container_layout.setAlignment(Qt.AlignTop)

        self.conn_scroll.setWidget(self.conn_container)
        conn_layout.addWidget(self.conn_scroll)

        self.empty_conn_label = QLabel("Este lugar no tiene conexiones de viaje a otros lugares.")
        self.empty_conn_label.setStyleSheet("color: #888; font-style: italic; padding: 6px;")
        self.conn_container_layout.addWidget(self.empty_conn_label)

        self.tab_widget.addTab(self.tab_connections, "Conexiones")

        # =====================================================================
        # PESTAÑA 3: LoreBlocks (Detección Cruzada)
        # =====================================================================
        self.tab_lore = QWidget()
        lore_layout = QVBoxLayout(self.tab_lore)

        info_lbl = QLabel(
            "Eventos y secretos narrativos vinculados directamente a este lugar (📍) "
            "o a personajes (👤) y objetos (📦) situados en él. Doble clic para editar."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 4px;")
        lore_layout.addWidget(info_lbl)

        self.lore_refs_widget = LoreReferenceListWidget(self)
        self.lore_refs_widget.lore_block_requested.connect(self.on_lore_block_selected)
        lore_layout.addWidget(self.lore_refs_widget)

        self.tab_widget.addTab(self.tab_lore, "LoreBlocks")

    def set_place(self, place: Place, all_places: List[Place], all_npcs: List[NPC]):
        self.place = place
        self.all_places = all_places or []
        self.all_npcs = all_npcs or []

        self.visible_entities_widget.set_controller(self.controller)

        if not place:
            self.id_label.setText("-")
            self.name_edit.clear()
            self.desc_edit.clear()
            self.visible_entities_widget.set_entity_ids([])
            self.refresh_connections()
            self.refresh_lore_references()
            return

        self.id_label.setText(f"📍 {place.id}")
        self.name_edit.setText(place.name)
        self.desc_edit.setPlainText(place.description or "")

        # Entidades visibles
        self.visible_entities_widget.set_entity_ids(place.visible_entities or [])

        # Conexiones
        self.refresh_connections()

        # LoreBlocks cruzados
        self.refresh_lore_references()

    def on_name_changed(self, text: str):
        if self.place:
            self.place.name = text

    def on_desc_changed(self):
        if self.place:
            self.place.description = self.desc_edit.toPlainText()

    def on_visible_entities_changed(self):
        if self.place:
            self.place.visible_entities = self.visible_entities_widget.get_entity_ids()
            self.refresh_lore_references()

    # --- GESTIÓN DE CONEXIONES LIMPIAS (SIN TABLAS) ---

    def refresh_connections(self):
        while self.conn_container_layout.count():
            item = self.conn_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.place or not self.place.connections:
            self.empty_conn_label = QLabel("Este lugar no tiene conexiones de viaje a otros lugares.")
            self.empty_conn_label.setStyleSheet("color: #888; font-style: italic; padding: 6px;")
            self.conn_container_layout.addWidget(self.empty_conn_label)
            return

        for direction, conn in self.place.connections.items():
            card = self._create_connection_card(
                direction, conn.target, conn.distance, conn.terrain_type, getattr(conn, "passable", True)
            )
            self.conn_container_layout.addWidget(card)

    def _create_connection_card(self, direction: str, target: str, distance: int, terrain: str, passable: bool = True) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #c8d8e8;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        dir_lbl = QLabel(f"<b>🧭 {direction}</b>")
        dir_lbl.setStyleSheet("color: #005a9e;")
        layout.addWidget(dir_lbl)

        arrow = QLabel("➔")
        arrow.setStyleSheet("color: #888;")
        layout.addWidget(arrow)

        target_lbl = QLabel(f"📍 <b>{target}</b>")
        layout.addWidget(target_lbl)

        info_lbl = QLabel(f"<span style='color: #666;'>📏 {distance} m</span> | <span style='color: #444;'>🏞️ {terrain}</span>")
        layout.addWidget(info_lbl)

        # Botón / Badge de estado de paso
        passable_btn = QPushButton("🟢 Abierta" if passable else "🔴 Bloqueada")
        passable_btn.setToolTip("Alternar paso (abrir o bloquear conexión)")
        passable_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                border: 1px solid {'#90ee90' if passable else '#ff9999'};
                background: {'#f0fff0' if passable else '#fff0f0'};
                color: {'#006600' if passable else '#990000'};
            }}
            QPushButton:hover {{
                background: {'#e0ffe0' if passable else '#ffe6e6'};
            }}
        """)
        passable_btn.clicked.connect(lambda _, d=direction: self.on_toggle_passable(d))
        layout.addWidget(passable_btn)

        layout.addStretch()

        del_btn = QPushButton("✕")
        del_btn.setToolTip("Eliminar conexión bidireccional")
        del_btn.setStyleSheet("border: none; background: transparent; color: #cc0000; font-weight: bold; font-size: 13px;")
        del_btn.clicked.connect(lambda _, d=direction, t=target: self.on_delete_connection(d, t))
        layout.addWidget(del_btn)

        return card

    def on_toggle_passable(self, direction: str):
        if not self.place:
            return
        self.controller.toggle_connection_passable(self.place.name, direction)
        self.refresh_connections()

    def on_add_connection(self):
        if not self.place:
            return

        dialog = ConnectionDialog(self.place, self.all_places, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dest_name, dir_ab, dir_ba, distance, terrain, passable = dialog.get_data()
            if not dest_name:
                QMessageBox.warning(self, "Error", "Debe seleccionar un lugar destino.")
                return

            try:
                self.controller.add_connection(self.place.name, dest_name, dir_ab, dir_ba, distance, terrain, passable)
                self.refresh_connections()
                QMessageBox.information(self, "Conexión Creada", f"Conexión bidireccional creada con '{dest_name}'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la conexión: {e}")


    def on_delete_connection(self, direction: str, target: str):
        if not self.place:
            return

        confirm = QMessageBox.question(
            self, "Eliminar Conexión",
            f"¿Estás seguro de eliminar la conexión '{direction}' hacia '{target}'?\n"
            f"Se eliminará automáticamente también la conexión de retorno en '{target}'.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.remove_connection(self.place.name, direction)
            self.refresh_connections()

    # --- RESOLUCIÓN DE LOREBLOCKS CRUZADOS ---

    def refresh_lore_references(self):
        if not self.place or not self.controller:
            self.lore_refs_widget.set_references([])
            return

        place_id = self.place.id
        lore_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])

        # Identificar NPCs en este lugar
        npcs_in_place = set()
        npc_names = {}
        for n in self.controller.get_npcs():
            if n.initial_place == place_id or place_id in (n.current_location or "") or n.id in (self.place.visible_entities or []):
                npcs_in_place.add(n.id)
                npc_names[n.id] = n.name

        # Identificar Objetos en este lugar
        items_in_place = set()
        item_names = {}
        for obj in getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", []):
            if obj.initial_place == place_id or obj.id in (self.place.visible_entities or []):
                items_in_place.add(obj.id)
                item_names[obj.id] = obj.name

        refs = []
        for b in lore_blocks:
            targets = set(getattr(b, "target_entities", []) or [])
            title = b.title or b.name or b.id

            # 1. Directo al lugar
            if place_id in targets:
                refs.append((b.id, title, "direct", self.place.name))
                continue

            # 2. Vía NPC
            matched_npc = targets.intersection(npcs_in_place)
            if matched_npc:
                first_npc = next(iter(matched_npc))
                refs.append((b.id, title, "npc", npc_names.get(first_npc, first_npc)))
                continue

            # 3. Vía Objeto
            matched_item = targets.intersection(items_in_place)
            if matched_item:
                first_item = next(iter(matched_item))
                refs.append((b.id, title, "item", item_names.get(first_item, first_item)))
                continue

        self.lore_refs_widget.set_references(refs)

    def on_lore_block_selected(self, lb_id: str):
        self.lore_block_requested.emit(lb_id)
        if self.parent_app and hasattr(self.parent_app, "navigate_to_lore_block"):
            self.parent_app.navigate_to_lore_block(lb_id)

    def on_delete_clicked(self):
        if self.place and self.parent_app and hasattr(self.parent_app, "delete_place"):
            self.parent_app.delete_place(self.place)
