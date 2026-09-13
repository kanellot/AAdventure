"""Vista para gestionar el catálogo independiente de Objetos e Items de la aventura."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QLabel,
)
from typing import List
from domains.items import Item
from editor.views.item_dialog import ItemDialog


class ObjectsCatalogForm(QWidget):
    """Vista de catálogo global de Objetos en el editor."""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)

        group = QGroupBox("Catálogo Independiente de Objetos / Items")
        group_layout = QVBoxLayout(group)

        desc = QLabel(
            "Los objetos pueden existir de forma independiente. Pueden tener asignado un lugar inicial "
            "o no tener ninguno asignado para aparecer dinámicamente mediante un efecto de LoreBlock."
        )
        desc.setWordWrap(True)
        group_layout.addWidget(desc)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Lugar Inicial", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.on_edit_object)
        group_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Añadir Objeto...")
        self.add_btn.clicked.connect(self.on_add_object)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Editar Objeto...")
        self.edit_btn.clicked.connect(self.on_edit_object)
        btn_layout.addWidget(self.edit_btn)

        self.del_btn = QPushButton("Eliminar Objeto")
        self.del_btn.clicked.connect(self.on_delete_object)
        btn_layout.addWidget(self.del_btn)

        group_layout.addLayout(btn_layout)
        layout.addWidget(group)

    def refresh_table(self):
        self.table.setRowCount(0)
        if not self.controller:
            return

        for obj in self.controller.objects:
            row = self.table.rowCount()
            self.table.insertRow(row)

            place_name = "(Ninguno / Por LoreBlock)"
            if obj.initial_place:
                p = self.controller.get_place_by_id(obj.initial_place) or self.controller.get_place_by_name(obj.initial_place)
                place_name = f"{p.name} ({p.id})" if p else obj.initial_place

            self.table.setItem(row, 0, QTableWidgetItem(obj.id))
            self.table.setItem(row, 1, QTableWidgetItem(obj.name))
            self.table.setItem(row, 2, QTableWidgetItem(place_name))
            self.table.setItem(row, 3, QTableWidgetItem(obj.state or "default"))

    def on_add_object(self):
        dialog = ItemDialog(controller=self.controller, parent=self)
        if dialog.exec():
            new_item = dialog.get_data()
            if self.controller:
                self.controller.objects.append(new_item)
                self.refresh_table()

    def on_edit_object(self):
        row = self.table.currentRow()
        if row < 0 or not self.controller:
            return

        obj_id = self.table.item(row, 0).text()
        obj = self.controller.get_object_by_id(obj_id)
        if not obj:
            return

        dialog = ItemDialog(item=obj, controller=self.controller, parent=self)
        if dialog.exec():
            updated = dialog.get_data()
            obj.name = updated.name
            obj.description = updated.description
            obj.state = updated.state
            obj.initial_place = updated.initial_place
            self.refresh_table()

    def on_delete_object(self):
        row = self.table.currentRow()
        if row < 0 or not self.controller:
            return

        obj_id = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Seguro que deseas eliminar el objeto '{obj_id}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.controller.remove_object(obj_id)
            self.refresh_table()
