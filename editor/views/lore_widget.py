from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QDialogButtonBox, QLabel, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from domains.lore import LoreBlock, LoreConditions, LoreEffects

class LoreBlockDialog(QDialog):
    """Diálogo modal para crear o editar un bloque de lore dinámico o secreto."""

    def __init__(self, lore_block: Optional[LoreBlock] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Bloque de Lore / Secreto")
        self.resize(550, 650)

        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QFormLayout(content_widget)

        # 1. Identificación básica
        self.id_edit = QLineEdit()
        form_layout.addRow("ID Único:", self.id_edit)

        self.title_edit = QLineEdit()
        form_layout.addRow("Título Descriptivo:", self.title_edit)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Reactivo (Se activa por intención/frase del jugador)", "reactive")
        self.mode_combo.addItem("Proactivo (Iniciativa propia del NPC al cumplir condiciones)", "proactive")
        form_layout.addRow("Modo de Activación:", self.mode_combo)

        # 2. Frases ancla (Triggers)
        self.phrases_edit = QTextEdit()
        self.phrases_edit.setPlaceholderText("Introduce una frase de ejemplo por línea...")
        self.phrases_edit.setMaximumHeight(90)
        form_layout.addRow("Frases Ancla (Embeddings):", self.phrases_edit)

        # 3. Directiva para el LLM
        self.directive_edit = QTextEdit()
        self.directive_edit.setPlaceholderText("Instrucción precisa para el LLM (ej: Ofrécele limpiar las ratas del sótano)...")
        self.directive_edit.setMaximumHeight(90)
        form_layout.addRow("Directiva para el LLM:", self.directive_edit)

        # 4. Condiciones de Desbloqueo
        cond_group = QGroupBox("Condiciones de Activación")
        cond_layout = QFormLayout(cond_group)

        self.min_affinity_spin = QDoubleSpinBox()
        self.min_affinity_spin.setRange(0.0, 1.0)
        self.min_affinity_spin.setSingleStep(0.05)
        self.min_affinity_spin.setValue(0.0)
        cond_layout.addRow("Afinidad Mínima (0.0 - 1.0):", self.min_affinity_spin)

        self.max_affinity_spin = QDoubleSpinBox()
        self.max_affinity_spin.setRange(0.0, 1.0)
        self.max_affinity_spin.setSingleStep(0.05)
        self.max_affinity_spin.setValue(1.0)
        cond_layout.addRow("Afinidad Máxima (0.0 - 1.0):", self.max_affinity_spin)

        self.gold_req_spin = QSpinBox()
        self.gold_req_spin.setRange(0, 99999)
        self.gold_req_spin.setValue(0)
        cond_layout.addRow("Oro Mínimo Requerido:", self.gold_req_spin)

        self.req_quests_edit = QLineEdit()
        self.req_quests_edit.setPlaceholderText("quest_1, quest_2 (separadas por coma)")
        cond_layout.addRow("Misiones Completadas Req.:", self.req_quests_edit)

        self.req_items_edit = QLineEdit()
        self.req_items_edit.setPlaceholderText("llave_hierro, mapa (separados por coma)")
        cond_layout.addRow("Objetos en Inventario Req.:", self.req_items_edit)

        form_layout.addRow(cond_group)

        # 5. Efectos y Mutaciones
        effects_group = QGroupBox("Efectos al Activarse (Causa-Efecto)")
        effects_layout = QFormLayout(effects_group)

        self.give_items_edit = QLineEdit()
        self.give_items_edit.setPlaceholderText("objeto1, objeto2")
        effects_layout.addRow("Entregar Objetos al Jugador:", self.give_items_edit)

        self.take_items_edit = QLineEdit()
        self.take_items_edit.setPlaceholderText("objeto1, objeto2")
        effects_layout.addRow("Retirar Objetos del Jugador:", self.take_items_edit)

        self.give_gold_spin = QSpinBox()
        self.give_gold_spin.setRange(0, 99999)
        effects_layout.addRow("Entregar Oro (+):", self.give_gold_spin)

        self.take_gold_spin = QSpinBox()
        self.take_gold_spin.setRange(0, 99999)
        effects_layout.addRow("Cobrar / Retirar Oro (-):", self.take_gold_spin)

        self.affinity_delta_spin = QDoubleSpinBox()
        self.affinity_delta_spin.setRange(-1.0, 1.0)
        self.affinity_delta_spin.setSingleStep(0.05)
        self.affinity_delta_spin.setValue(0.0)
        effects_layout.addRow("Cambio de Afinidad (+/-):", self.affinity_delta_spin)

        self.unlock_quests_edit = QLineEdit()
        self.unlock_quests_edit.setPlaceholderText("quest_sotano_ratas")
        effects_layout.addRow("Activar Misiones:", self.unlock_quests_edit)

        self.unlock_places_edit = QLineEdit()
        self.unlock_places_edit.setPlaceholderText("sotano, tunel_ladrones")
        effects_layout.addRow("Desbloquear Lugares:", self.unlock_places_edit)

        self.once_check = QCheckBox("De un solo uso (No se repite tras revelarse)")
        self.once_check.setChecked(True)
        effects_layout.addRow(self.once_check)

        self.revealed_check = QCheckBox("Ya revelado / Ya entregado")
        self.revealed_check.setChecked(False)
        effects_layout.addRow(self.revealed_check)

        form_layout.addRow(effects_group)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Botones Aceptar / Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if lore_block:
            self.set_data(lore_block)

    def set_data(self, block: LoreBlock):
        self.id_edit.setText(block.id)
        self.title_edit.setText(block.title or "")
        
        idx = self.mode_combo.findData(block.trigger_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        self.phrases_edit.setPlainText("\n".join(block.trigger_phrases))
        self.directive_edit.setPlainText(block.directive)

        # Condiciones
        self.min_affinity_spin.setValue(block.conditions.min_affinity)
        self.max_affinity_spin.setValue(block.conditions.max_affinity)
        self.gold_req_spin.setValue(block.conditions.required_gold)
        self.req_quests_edit.setText(", ".join(block.conditions.required_quests))
        self.req_items_edit.setText(", ".join(block.conditions.required_items))

        # Efectos
        self.give_items_edit.setText(", ".join(block.effects.give_items))
        self.take_items_edit.setText(", ".join(block.effects.take_items))
        self.give_gold_spin.setValue(block.effects.give_gold)
        self.take_gold_spin.setValue(block.effects.take_gold)
        self.affinity_delta_spin.setValue(block.effects.affinity_delta)
        self.unlock_quests_edit.setText(", ".join(block.effects.unlock_quests))
        self.unlock_places_edit.setText(", ".join(block.effects.unlock_places))
        self.once_check.setChecked(block.once)
        self.revealed_check.setChecked(block.revealed)

    def on_accept(self):
        if not self.id_edit.text().strip():
            QMessageBox.warning(self, "Validación", "El ID del bloque de lore es obligatorio.")
            return
        if not self.directive_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validación", "La directiva para el LLM es obligatoria.")
            return
        self.accept()

    def get_data(self) -> LoreBlock:
        phrases = [p.strip() for p in self.phrases_edit.toPlainText().split("\n") if p.strip()]
        req_quests = [q.strip() for q in self.req_quests_edit.text().split(",") if q.strip()]
        req_items = [i.strip() for i in self.req_items_edit.text().split(",") if i.strip()]

        give_items = [i.strip() for i in self.give_items_edit.text().split(",") if i.strip()]
        take_items = [i.strip() for i in self.take_items_edit.text().split(",") if i.strip()]
        unlock_quests = [q.strip() for q in self.unlock_quests_edit.text().split(",") if q.strip()]
        unlock_places = [p.strip() for p in self.unlock_places_edit.text().split(",") if p.strip()]

        conditions = LoreConditions(
            min_affinity=self.min_affinity_spin.value(),
            max_affinity=self.max_affinity_spin.value(),
            required_gold=self.gold_req_spin.value(),
            required_quests=req_quests,
            required_items=req_items
        )

        effects = LoreEffects(
            give_items=give_items,
            take_items=take_items,
            give_gold=self.give_gold_spin.value(),
            take_gold=self.take_gold_spin.value(),
            affinity_delta=self.affinity_delta_spin.value(),
            unlock_quests=unlock_quests,
            unlock_places=unlock_places
        )

        return LoreBlock(
            id=self.id_edit.text().strip(),
            title=self.title_edit.text().strip() or None,
            trigger_mode=self.mode_combo.currentData(),
            trigger_phrases=phrases,
            directive=self.directive_edit.toPlainText().strip(),
            conditions=conditions,
            effects=effects,
            once=self.once_check.isChecked(),
            revealed=self.revealed_check.isChecked()
        )


class LoreBlockTableWidget(QWidget):
    """Widget reutilizable que muestra y permite gestionar la lista de LoreBlocks de cualquier entidad."""

    lore_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lore_blocks: List[LoreBlock] = []

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Título / Resumen", "Modo", "Afinidad Mín.", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.on_edit_block)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Añadir Lore / Secreto...")
        self.add_btn.clicked.connect(self.on_add_block)
        self.edit_btn = QPushButton("Editar Seleccionado...")
        self.edit_btn.clicked.connect(self.on_edit_block)
        self.del_btn = QPushButton("Eliminar Seleccionado")
        self.del_btn.clicked.connect(self.on_delete_block)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)

    def set_lore_blocks(self, lore_blocks: List[LoreBlock]):
        self.lore_blocks = lore_blocks or []
        self.populate_table()

    def get_lore_blocks(self) -> List[LoreBlock]:
        return self.lore_blocks

    def populate_table(self):
        self.table.setRowCount(0)
        for block in self.lore_blocks:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(block.id))
            title = block.title or (block.directive[:40] + "..." if len(block.directive) > 40 else block.directive)
            self.table.setItem(row, 1, QTableWidgetItem(title))
            self.table.setItem(row, 2, QTableWidgetItem(block.trigger_mode.capitalize()))
            self.table.setItem(row, 3, QTableWidgetItem(f"{block.conditions.min_affinity:.2f}"))
            status = "Revelado" if block.revealed else "Oculto"
            self.table.setItem(row, 4, QTableWidgetItem(status))

    def on_add_block(self):
        dialog = LoreBlockDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_block = dialog.get_data()
            self.lore_blocks.append(new_block)
            self.populate_table()
            self.lore_changed.emit()

    def on_edit_block(self):
        selected_row = self.table.currentRow()
        if selected_row < 0 or selected_row >= len(self.lore_blocks):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una fila para editar.")
            return

        block = self.lore_blocks[selected_row]
        dialog = LoreBlockDialog(lore_block=block, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_block = dialog.get_data()
            self.lore_blocks[selected_row] = updated_block
            self.populate_table()
            self.lore_changed.emit()

    def on_delete_block(self):
        selected_row = self.table.currentRow()
        if selected_row < 0 or selected_row >= len(self.lore_blocks):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una fila para eliminar.")
            return

        block = self.lore_blocks[selected_row]
        confirm = QMessageBox.question(
            self, "Eliminar Lore",
            f"¿Estás seguro de eliminar el bloque '{block.id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.lore_blocks.pop(selected_row)
            self.populate_table()
            self.lore_changed.emit()
