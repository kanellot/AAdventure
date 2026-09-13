"""Diálogo para crear y editar objetos (Items) independientes o ligados a un lugar."""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDialogButtonBox,
    QVBoxLayout,
    QMessageBox,
    QComboBox,
    QScrollArea,
    QWidget,
)
from domains.items import Item


class ItemDialog(QDialog):
    """Diálogo modal para crear o editar un objeto del mundo."""

    def __init__(self, item: Optional[Item] = None, controller=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Objeto / Item")
        self.resize(450, 380)
        self.controller = controller

        main_layout = QVBoxLayout(self)

        content_widget = QWidget()
        form_layout = QFormLayout(content_widget)

        # 1. Identificación
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("item_llave_antigua")
        form_layout.addRow("ID Único:", self.id_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Llave de Latón")
        form_layout.addRow("Nombre:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Una llave pesada cubierta de pátina verde...")
        self.desc_edit.setMaximumHeight(80)
        form_layout.addRow("Descripción:", self.desc_edit)

        self.state_edit = QLineEdit()
        self.state_edit.setText("default")
        self.state_edit.setPlaceholderText("default, oxidada, rota, abierta...")
        form_layout.addRow("Estado inicial:", self.state_edit)

        # 2. Lugar inicial
        self.initial_place_combo = QComboBox()
        self.initial_place_combo.addItem("(Ninguno / Aparece por evento o LoreBlock)", None)
        if controller:
            for p in controller.get_all_places():
                self.initial_place_combo.addItem(f"{p.name} ({p.id})", p.id)
        form_layout.addRow("Lugar Inicial:", self.initial_place_combo)

        main_layout.addWidget(content_widget)

        # Botones Aceptar / Cancelar
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.on_accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

        if item:
            self.set_data(item)

    def set_data(self, item: Item):
        self.id_edit.setText(item.id)
        self.name_edit.setText(item.name)
        self.desc_edit.setPlainText(item.description or "")
        self.state_edit.setText(item.state or "default")

        # Seleccionar lugar inicial
        idx = 0
        if item.initial_place:
            for i in range(1, self.initial_place_combo.count()):
                pid = self.initial_place_combo.itemData(i)
                if pid == item.initial_place or item.initial_place in self.initial_place_combo.itemText(i):
                    idx = i
                    break
        self.initial_place_combo.setCurrentIndex(idx)

    def on_accept(self):
        if not self.id_edit.text().strip():
            QMessageBox.warning(self, "Validación", "El ID del objeto es obligatorio.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validación", "El nombre del objeto es obligatorio.")
            return
        self.accept()

    def get_data(self) -> Item:
        selected_pid = self.initial_place_combo.currentData()
        return Item(
            id=self.id_edit.text().strip(),
            name=self.name_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            state=self.state_edit.text().strip() or "default",
            initial_place=selected_pid,
        )
