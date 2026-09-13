"""Formulario integrado para editar un Objeto / Item:
1. Pestaña General: ID, Nombre, Descripción, Lugar Inicial (📍) y Estado.
2. Pestaña LoreBlocks: LoreBlocks que tienen como objetivo a este objeto, con doble clic para editar.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QLabel,
    QComboBox,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from domains.items import Item
from editor.views.compact_widgets import LoreReferenceListWidget


class ObjectForm(QWidget):
    """Formulario dedicado para la edición de un Objeto (Item) independiente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.item: Optional[Item] = None
        self.parent_app = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con botón de eliminar
        top_bar = QHBoxLayout()
        self.header_title = QLabel("<b>📦 Objeto / Item</b>")
        self.header_title.setStyleSheet("font-size: 14px; color: #d35400;")
        top_bar.addWidget(self.header_title)
        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar este objeto")
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
        # Pestaña 1: Datos Generales
        # =====================================================================
        self.tab_general = QWidget()
        general_layout = QFormLayout(self.tab_general)

        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold; color: #d35400;")
        general_layout.addRow("ID del Objeto:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del objeto...")
        self.name_edit.textChanged.connect(self.on_name_changed)
        general_layout.addRow("Nombre del Objeto:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Descripción visual o propiedades del objeto...")
        self.desc_edit.setMaximumHeight(85)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        general_layout.addRow("Descripción:", self.desc_edit)

        self.initial_place_combo = QComboBox()
        self.initial_place_combo.currentTextChanged.connect(self.on_initial_place_changed)
        general_layout.addRow("Lugar Inicial:", self.initial_place_combo)

        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("default, oxidada, mágica, oculta...")
        self.state_edit.textChanged.connect(self.on_state_changed)
        general_layout.addRow("Estado Inicial:", self.state_edit)

        self.tab_widget.addTab(self.tab_general, "General")

        # =====================================================================
        # Pestaña 2: LoreBlocks vinculados
        # =====================================================================
        self.tab_lore = QWidget()
        lore_layout = QVBoxLayout(self.tab_lore)

        info_lbl = QLabel(
            "Eventos y bloques de lore que tienen como objetivo a este objeto (📦) "
            "o que lo entregan/retiran como efecto narrativo. Doble clic para editar."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 4px;")
        lore_layout.addWidget(info_lbl)

        self.lore_refs_widget = LoreReferenceListWidget(self)
        self.lore_refs_widget.lore_block_requested.connect(self.on_lore_block_selected)
        lore_layout.addWidget(self.lore_refs_widget)

        self.tab_widget.addTab(self.tab_lore, "LoreBlocks")

    def set_object(self, item: Optional[Item]):
        self.item = item

        # Poblar combo de lugares con emojis
        try:
            self.initial_place_combo.currentTextChanged.disconnect(self.on_initial_place_changed)
        except Exception:
            pass

        self.initial_place_combo.clear()
        self.initial_place_combo.addItem("(Ninguno / Aparece por evento o LoreBlock)", None)

        controller = getattr(self.parent_app, "controller", None)
        all_places = controller.get_all_places() if controller else []
        for p in all_places:
            self.initial_place_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

        if not item:
            self.id_label.setText("-")
            self.name_edit.clear()
            self.desc_edit.clear()
            self.state_edit.clear()
            self.lore_refs_widget.set_references([])
            return

        self.id_label.setText(f"📦 {item.id}")
        self.name_edit.setText(item.name)
        self.desc_edit.setPlainText(item.description or "")
        self.state_edit.setText(item.state or "default")

        # Seleccionar lugar inicial
        current_init = item.initial_place
        idx = 0
        if current_init:
            for i in range(1, self.initial_place_combo.count()):
                pid = self.initial_place_combo.itemData(i)
                if pid == current_init or current_init in self.initial_place_combo.itemText(i):
                    idx = i
                    break
        self.initial_place_combo.setCurrentIndex(idx)
        self.initial_place_combo.currentTextChanged.connect(self.on_initial_place_changed)

        # LoreBlocks vinculados
        self.refresh_lore_references()

    def refresh_lore_references(self):
        if not self.item:
            self.lore_refs_widget.set_references([])
            return

        controller = getattr(self.parent_app, "controller", None)
        if not controller:
            self.lore_refs_widget.set_references([])
            return

        lore_blocks = getattr(controller, "get_lore_blocks", lambda: [])() or getattr(controller, "lore_blocks", [])
        item_id = self.item.id

        refs = []
        for b in lore_blocks:
            targets = set(getattr(b, "target_entities", []) or [])
            title = b.title or b.name or b.id
            is_target = item_id in targets

            # Comprobar si además está en efectos
            effects = getattr(b, "effects", None)
            is_in_effects = False
            if effects:
                if item_id in (effects.give_items or []) or item_id in (effects.take_items or []):
                    is_in_effects = True

            if is_target or is_in_effects:
                refs.append((b.id, title, "item", self.item.name))

        self.lore_refs_widget.set_references(refs)

    def on_name_changed(self, text: str):
        if self.item:
            self.item.name = text

    def on_desc_changed(self):
        if self.item:
            self.item.description = self.desc_edit.toPlainText()

    def on_initial_place_changed(self, _text: str):
        if self.item:
            selected_pid = self.initial_place_combo.currentData()
            self.item.initial_place = selected_pid

    def on_state_changed(self, text: str):
        if self.item:
            self.item.state = text

    def on_lore_block_selected(self, lb_id: str):
        if self.parent_app and hasattr(self.parent_app, "navigate_to_lore_block"):
            self.parent_app.navigate_to_lore_block(lb_id)

    def on_delete_clicked(self):
        if self.item and self.parent_app and hasattr(self.parent_app, "delete_object"):
            self.parent_app.delete_object(self.item)
