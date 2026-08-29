from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QGroupBox,
    QCheckBox, QScrollArea, QHeaderView, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from typing import List
from domains import Place, NPC
from editor.views.dialogs import ConnectionDialog

class PlaceForm(QWidget):
    """
    Formulario para editar un Lugar (Place), incluyendo NPCs visibles
    y sus conexiones de viaje a otros lugares.
    """
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.place: Place = None
        self.all_npcs: List[NPC] = []
        self.all_places: List[Place] = []
        self.updating_checkboxes = False

        # Layout Principal
        main_layout = QVBoxLayout(self)

        # 1. Campos Básicos
        basic_group = QGroupBox("Propiedades del Lugar")
        form_layout = QFormLayout(basic_group)
        self.id_label = QLabel()
        form_layout.addRow("ID del Lugar:", self.id_label)
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        form_layout.addRow("Nombre del Lugar:", self.name_edit)
        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        form_layout.addRow("Descripción:", self.desc_edit)
        main_layout.addWidget(basic_group)

        # 2. Checklist de NPCs visibles
        npcs_group = QGroupBox("NPCs Visibles en este Lugar")
        npcs_layout = QVBoxLayout(npcs_group)
        self.npc_scroll = QScrollArea()
        self.npc_scroll.setWidgetResizable(True)
        self.npc_scroll_content = QWidget()
        self.npc_scroll_layout = QVBoxLayout(self.npc_scroll_content)
        self.npc_scroll_layout.setAlignment(Qt.AlignTop)
        self.npc_scroll.setWidget(self.npc_scroll_content)
        npcs_layout.addWidget(self.npc_scroll)
        main_layout.addWidget(npcs_group)

        # 3. Tabla de Conexiones
        conn_group = QGroupBox("Conexiones de Viaje")
        conn_layout = QVBoxLayout(conn_group)
        
        self.conn_table = QTableWidget(0, 4)
        self.conn_table.setHorizontalHeaderLabels(["Dirección", "Lugar Destino", "Distancia", "Terreno"])
        self.conn_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.conn_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.conn_table.setSelectionMode(QTableWidget.SingleSelection)
        conn_layout.addWidget(self.conn_table)

        # Botones de Conexión
        btn_layout = QHBoxLayout()
        self.add_conn_btn = QPushButton("Añadir Conexión...")
        self.add_conn_btn.clicked.connect(self.on_add_connection)
        self.del_conn_btn = QPushButton("Eliminar Conexión Seleccionada")
        self.del_conn_btn.clicked.connect(self.on_delete_connection)
        btn_layout.addWidget(self.add_conn_btn)
        btn_layout.addWidget(self.del_conn_btn)
        conn_layout.addLayout(btn_layout)
        
        main_layout.addWidget(conn_group)

    def set_place(self, place: Place, all_places: List[Place], all_npcs: List[NPC]):
        self.place = place
        self.all_places = all_places
        self.all_npcs = all_npcs

        if place:
            self.id_label.setText(place.id)
            self.name_edit.setText(place.name)
            self.desc_edit.setPlainText(place.description)

            # Poblar y marcar la lista de NPCs
            self.populate_npcs()

            # Poblar la tabla de conexiones
            self.populate_connections()

    def populate_npcs(self):
        # Limpiar layout de checkboxes anterior
        self.updating_checkboxes = True
        while self.npc_scroll_layout.count():
            child = self.npc_scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Crear nuevos checkboxes
        for npc in self.all_npcs:
            cb = QCheckBox(f"{npc.name} ({npc.id})")
            # Si el NPC ID está en visible_entities de este place, se marca
            if self.place and npc.id in self.place.visible_entities:
                cb.setChecked(True)
            cb.stateChanged.connect(lambda state, nid=npc.id: self.on_npc_check_changed(nid, state))
            self.npc_scroll_layout.addWidget(cb)
        self.updating_checkboxes = False

    def populate_connections(self):
        self.conn_table.setRowCount(0)
        if not self.place or not self.place.connections:
            return

        for direction, conn in self.place.connections.items():
            row = self.conn_table.rowCount()
            self.conn_table.insertRow(row)

            # Dirección
            self.conn_table.setItem(row, 0, QTableWidgetItem(direction))
            # Destino
            self.conn_table.setItem(row, 1, QTableWidgetItem(conn.target))
            # Distancia
            self.conn_table.setItem(row, 2, QTableWidgetItem(f"{conn.distance} m"))
            # Terreno
            self.conn_table.setItem(row, 3, QTableWidgetItem(conn.terrain_type))

    def on_name_changed(self, text: str):
        if self.place:
            self.place.name = text

    def on_desc_changed(self):
        if self.place:
            self.place.description = self.desc_edit.toPlainText()

    def on_npc_check_changed(self, npc_id: str, state: int):
        if self.updating_checkboxes or not self.place:
            return
        
        is_checked = state == Qt.Checked.value or state == 2
        if is_checked:
            if npc_id not in self.place.visible_entities:
                self.place.visible_entities.append(npc_id)
        else:
            if npc_id in self.place.visible_entities:
                self.place.visible_entities.remove(npc_id)

    def on_add_connection(self):
        if not self.place:
            return

        # Abrir el ConnectionDialog
        dialog = ConnectionDialog(self.place, self.all_places, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dest_name, dir_ab, dir_ba, distance, terrain = dialog.get_data()
            if not dest_name:
                QMessageBox.warning(self, "Error", "Debe seleccionar un lugar destino.")
                return

            try:
                # Añadir la conexión a través del controlador
                self.controller.add_connection(self.place.name, dest_name, dir_ab, dir_ba, distance, terrain)
                self.populate_connections()
                QMessageBox.information(self, "Éxito", f"Conexión bidireccional creada entre '{self.place.name}' y '{dest_name}'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la conexión: {e}")

    def on_delete_connection(self):
        selected_row = self.conn_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selección", "Por favor, selecciona una fila de la tabla de conexiones para eliminar.")
            return

        direction = self.conn_table.item(selected_row, 0).text()
        target = self.conn_table.item(selected_row, 1).text()

        confirm = QMessageBox.question(
            self, "Eliminar Conexión",
            f"¿Estás seguro de eliminar la conexión '{direction}' hacia '{target}'?\n"
            f"Esto también eliminará automáticamente la conexión de retorno en '{target}'.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.controller.remove_connection(self.place.name, direction)
            self.populate_connections()
            QMessageBox.information(self, "Éxito", "Conexión bidireccional eliminada.")
