"""Formulario dedicado para la edición de un Ítem independiente:
ID, Nombre, Descripción, Ubicación Inicial (📍) y Estado.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QLabel,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from domains.items import Item


class ItemForm(QWidget):
    """Formulario dedicado para la edición de un Ítem independiente."""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.item: Optional[Item] = None
        self.parent_app = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con botón de eliminar
        top_bar = QHBoxLayout()
        self.header_title = QLabel("<b>📦 Ítem</b>")
        self.header_title.setStyleSheet("font-size: 14px; color: #d35400;")
        top_bar.addWidget(self.header_title)
        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar este ítem de la historia")
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

        # Campos del formulario
        form_layout = QFormLayout()

        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold; color: #d35400;")
        form_layout.addRow("ID del Ítem:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del ítem...")
        self.name_edit.textChanged.connect(self.on_name_changed)
        form_layout.addRow("Nombre del Ítem:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Descripción visual o propiedades del ítem...")
        self.desc_edit.setMaximumHeight(85)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        form_layout.addRow("Descripción:", self.desc_edit)

        self.initial_location_combo = QComboBox()
        self.initial_location_combo.currentTextChanged.connect(self.on_initial_location_changed)
        form_layout.addRow("Ubicación Inicial:", self.initial_location_combo)

        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("default, oxidada, mágica, oculta...")
        self.state_edit.textChanged.connect(self.on_state_changed)
        form_layout.addRow("Estado Inicial:", self.state_edit)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

    def set_item(self, item: Optional[Item]):
        self.item = item

        try:
            self.initial_location_combo.currentTextChanged.disconnect(self.on_initial_location_changed)
        except Exception:
            pass

        self.initial_location_combo.clear()
        self.initial_location_combo.addItem("(Ninguno / Aparece por evento o en inventario)", None)

        controller = self.controller or getattr(self.parent_app, "controller", None)
        all_places = controller.get_all_places() if controller else []
        for p in all_places:
            self.initial_location_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

        if not item:
            self.id_label.setText("-")
            self.name_edit.clear()
            self.desc_edit.clear()
            self.state_edit.clear()
            return

        self.id_label.setText(f"📦 {item.id}")
        self.name_edit.setText(item.name)
        self.desc_edit.setPlainText(item.description or "")
        self.state_edit.setText(item.state or "default")

        # Seleccionar ubicación inicial
        current_init = item.initial_location
        idx = 0
        if current_init:
            for i in range(1, self.initial_location_combo.count()):
                pid = self.initial_location_combo.itemData(i)
                if pid == current_init or current_init in self.initial_location_combo.itemText(i):
                    idx = i
                    break
        self.initial_location_combo.setCurrentIndex(idx)
        self.initial_location_combo.currentTextChanged.connect(self.on_initial_location_changed)

    def on_name_changed(self, text: str):
        if self.item:
            self.item.name = text

    def on_desc_changed(self):
        if self.item:
            self.item.description = self.desc_edit.toPlainText()

    def on_initial_location_changed(self, _text: str):
        if self.item:
            selected_pid = self.initial_location_combo.currentData()
            self.item.initial_location = selected_pid

    def on_state_changed(self, text: str):
        if self.item:
            self.item.state = text

    def on_delete_clicked(self):
        if self.item and self.parent_app and hasattr(self.parent_app, "delete_item"):
            self.parent_app.delete_item(self.item)
