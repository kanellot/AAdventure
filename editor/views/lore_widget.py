"""Widgets visuales y diálogos para la gestión de LoreBlocks (HSM) y Condiciones."""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QDialogButtonBox, QLabel, QTabWidget, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from domains.lore import EntityCondition, LoreBlock, LoreBlockState, LoreEffects


class ConditionDialog(QDialog):
    """Diálogo modal para crear o editar una EntityCondition individual con selección estricta desde lista."""

    def __init__(self, condition: Optional[EntityCondition] = None, controller=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Condición")
        self.resize(440, 280)
        self.controller = controller

        layout = QFormLayout(self)

        # 1. Tipo de Entidad
        self.type_combo = QComboBox()
        self.type_combo.addItem("Lugar (Place)", "place")
        self.type_combo.addItem("Personaje (NPC)", "npc")
        self.type_combo.addItem("Objeto (Item)", "item")
        self.type_combo.addItem("Otro LoreBlock", "loreblock")
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        layout.addRow("Tipo de Entidad:", self.type_combo)

        # 2. Selector Estricto de Entidad (no editable manualmente)
        self.id_combo = QComboBox()
        self.id_combo.setEditable(False)
        layout.addRow("Entidad Objetivo:", self.id_combo)

        # 3. Subcondición
        self.sub_combo = QComboBox()
        self.sub_combo.currentIndexChanged.connect(self.on_sub_changed)
        layout.addRow("Subcondición:", self.sub_combo)

        # 4. Valor numérico (afinidad o cantidad de oro)
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0.0, 99999.0)
        self.value_spin.setSingleStep(0.05)
        self.value_spin.setValue(0.5)
        self.value_row_label = QLabel("Valor Requerido:")
        layout.addRow(self.value_row_label, self.value_spin)

        # 5. Negación NOT
        self.negated_check = QCheckBox("Invertir / Negar condición (NOT)")
        layout.addRow(self.negated_check)

        # Botones
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.on_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.on_type_changed()

        if condition:
            self.set_data(condition)

    def on_type_changed(self):
        etype = self.type_combo.currentData()
        self.sub_combo.clear()
        self.id_combo.clear()

        if etype == "place":
            self.sub_combo.addItem("known (A la vista / Descubierto)", "known")
            self.sub_combo.addItem("current_location (Ubicación actual del jugador)", "current_location")
            if self.controller:
                places = self.controller.get_all_places()
                for p in places:
                    self.id_combo.addItem(f"{p.name} ({p.id})", p.id)

        elif etype == "npc":
            self.sub_combo.addItem("known (Conocido por el jugador)", "known")
            self.sub_combo.addItem("affinity (Nivel mínimo de afinidad)", "affinity")
            if self.controller:
                for n in self.controller.get_npcs():
                    self.id_combo.addItem(f"{n.name} ({n.id})", n.id)

        elif etype == "item":
            self.sub_combo.addItem("have (En el inventario del jugador)", "have")
            self.sub_combo.addItem("known (Conocido / Visto por el jugador)", "known")
            self.id_combo.addItem("Oro (Monedas / Riqueza)", "gold")
            if self.controller:
                objects = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
                for obj in objects:
                    self.id_combo.addItem(f"{obj.name} ({obj.id})", obj.id)

        elif etype == "loreblock":
            self.sub_combo.addItem("done (En estado Done / Completado)", "done")
            self.sub_combo.addItem("active (En estado Activo)", "active")
            self.sub_combo.addItem("any_child_done (Cualquier sub-bloque hijo completado)", "any_child_done")
            self.id_combo.addItem("(Este mismo bloque padre)", "")
            if self.controller:
                lore_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])
                for b in lore_blocks:
                    title = b.title or b.name or b.id
                    prefix = f"[Sub-bloque de {b.parent_id}] " if getattr(b, "parent_id", None) else "[Raíz] "
                    self.id_combo.addItem(f"{prefix}{title} ({b.id})", b.id)

        self.on_sub_changed()

    def on_sub_changed(self):
        sub = self.sub_combo.currentData()
        etype = self.type_combo.currentData()
        ent_id = self.id_combo.currentData()

        show_value = (sub == "affinity") or (etype == "item" and ent_id == "gold")
        if sub == "affinity":
            self.value_spin.setRange(0.0, 1.0)
            self.value_spin.setDecimals(2)
            self.value_spin.setSingleStep(0.05)
            self.value_row_label.setText("Nivel Mínimo Afinidad (0.0 - 1.0):")
        elif ent_id == "gold":
            self.value_spin.setRange(0.0, 99999.0)
            self.value_spin.setDecimals(0)
            self.value_spin.setSingleStep(10.0)
            self.value_row_label.setText("Cantidad de Oro Requerida:")

        self.value_spin.setVisible(show_value)
        self.value_row_label.setVisible(show_value)

    def on_accept(self):
        raw_id = self.id_combo.currentData()
        if not raw_id:
            QMessageBox.warning(self, "Validación", "Debes seleccionar una entidad de la lista.")
            return
        self.accept()

    def get_data(self) -> EntityCondition:
        etype = self.type_combo.currentData()
        ent_id = self.id_combo.currentData()
        sub = self.sub_combo.currentData()
        val = self.value_spin.value() if ((sub == "affinity") or (ent_id == "gold")) else None
        return EntityCondition(
            entity_type=etype,
            entity_id=ent_id,
            sub_condition=sub,
            value=val,
            is_negated=self.negated_check.isChecked(),
        )

    def set_data(self, cond: EntityCondition):
        idx = self.type_combo.findData(cond.entity_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Buscar por currentData o texto
        idx_id = -1
        for i in range(self.id_combo.count()):
            data_val = self.id_combo.itemData(i)
            text_val = self.id_combo.itemText(i)
            if data_val == cond.entity_id or cond.entity_id in text_val:
                idx_id = i
                break

        if idx_id >= 0:
            self.id_combo.setCurrentIndex(idx_id)
        else:
            self.id_combo.addItem(f"{cond.entity_id} [Externo]", cond.entity_id)
            self.id_combo.setCurrentIndex(self.id_combo.count() - 1)

        idx_sub = self.sub_combo.findData(cond.sub_condition)
        if idx_sub >= 0:
            self.sub_combo.setCurrentIndex(idx_sub)

        if cond.value is not None:
            self.value_spin.setValue(float(cond.value))

        self.negated_check.setChecked(cond.is_negated)


class LoreBlockDialog(QDialog):
    """Diálogo modal compacto organizado por pestañas para configurar un LoreBlock (HSM)."""

    def __init__(self, lore_block: Optional[LoreBlock] = None, controller=None, initial_parent_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar LoreBlock (HSM)")
        self.resize(680, 560)
        self.controller = controller

        self.conditions: List[EntityCondition] = []
        self.exit_conditions: List[EntityCondition] = []

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        # =====================================================================
        # PESTAÑA 1: General y Entidades Afectadas
        # =====================================================================
        tab_general = QWidget()
        gen_layout = QVBoxLayout(tab_general)

        # Fila 1: ID y Título
        row1_layout = QHBoxLayout()
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("ej. pista_tabernero_mago")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título descriptivo del secreto...")
        row1_layout.addWidget(QLabel("ID Único:"))
        row1_layout.addWidget(self.id_edit)
        row1_layout.addWidget(QLabel("Título:"))
        row1_layout.addWidget(self.title_edit)
        gen_layout.addLayout(row1_layout)

        # Fila 1b: Carpeta / Bloque Padre HSM
        row_parent_layout = QHBoxLayout()
        self.parent_combo = QComboBox()
        self.parent_combo.setEditable(False)
        row_parent_layout.addWidget(QLabel("Carpeta / Bloque Padre:"))
        row_parent_layout.addWidget(self.parent_combo)
        gen_layout.addLayout(row_parent_layout)

        # Fila 2: Estado HSM y Modo
        row2_layout = QHBoxLayout()
        self.state_combo = QComboBox()
        self.state_combo.addItem("Unknown (No descubierto)", "unknown")
        self.state_combo.addItem("Active (Activo / En curso)", "active")
        self.state_combo.addItem("Done (Completado / Resuelto)", "done")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Reactivo (Se activa por intención/frase del jugador)", "reactive")
        self.mode_combo.addItem("Proactivo (Iniciativa al cumplir condiciones)", "proactive")

        row2_layout.addWidget(QLabel("Estado:"))
        row2_layout.addWidget(self.state_combo)
        row2_layout.addWidget(QLabel("Modo:"))
        row2_layout.addWidget(self.mode_combo)
        gen_layout.addLayout(row2_layout)

        # Grupo: Entidades Objetivo (target_entities)
        target_group = QGroupBox("Entidades Afectadas (Inyección de Prompt en Diálogo, Explicación o Movimiento)")
        target_vbox = QVBoxLayout(target_group)

        self.target_filter = QLineEdit()
        self.target_filter.setPlaceholderText("Filtrar entidades por nombre o ID...")
        self.target_filter.textChanged.connect(self.filter_target_entities)
        target_vbox.addWidget(self.target_filter)

        self.target_list = QListWidget()
        self.target_list.setMaximumHeight(115)
        self.target_list.itemChanged.connect(self.on_target_selection_changed)
        target_vbox.addWidget(self.target_list)

        self.target_summary_label = QLabel("Afecta a: (Ninguna entidad seleccionada)")
        self.target_summary_label.setStyleSheet("color: #007acc; font-weight: bold;")
        target_vbox.addWidget(self.target_summary_label)

        gen_layout.addWidget(target_group)

        # Directiva para el LLM
        gen_layout.addWidget(QLabel("Directiva para el LLM:"))
        self.directive_edit = QTextEdit()
        self.directive_edit.setPlaceholderText("Instrucción precisa que se inyectará al Dungeon Master / NPC...")
        self.directive_edit.setMaximumHeight(65)
        gen_layout.addWidget(self.directive_edit)

        # Reconocimiento RAG y frases ancla
        rag_group = QGroupBox("Reconocimiento Semántico RAG (Frases Antena)")
        rag_vbox = QVBoxLayout(rag_group)
        self.rag_check = QCheckBox("Activar similitud por embeddings de texto")
        self.rag_check.setChecked(True)
        self.rag_check.toggled.connect(self.on_rag_toggled)
        rag_vbox.addWidget(self.rag_check)

        self.phrases_edit = QTextEdit()
        self.phrases_edit.setPlaceholderText("Introduce una frase gatillo por línea...")
        self.phrases_edit.setMaximumHeight(50)
        rag_vbox.addWidget(self.phrases_edit)
        gen_layout.addWidget(rag_group)

        self.tab_widget.addTab(tab_general, "1. General y Objetivos")

        # =====================================================================
        # PESTAÑA 2: Condiciones de Activación (1 a N)
        # =====================================================================
        tab_conds = QWidget()
        cond_layout = QVBoxLayout(tab_conds)

        cond_info = QLabel("El bloque se activa cuando se cumplen conjuntamente todas estas condiciones (AND):")
        cond_layout.addWidget(cond_info)

        self.cond_table = QTableWidget(0, 5)
        self.cond_table.setHorizontalHeaderLabels(["Negado", "Tipo", "Entidad", "Condición", "Valor"])
        self.cond_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cond_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cond_table.setSelectionMode(QTableWidget.SingleSelection)
        self.cond_table.doubleClicked.connect(self.on_edit_condition)
        cond_layout.addWidget(self.cond_table)

        btn_cond_layout = QHBoxLayout()
        self.add_cond_btn = QPushButton("Añadir Condición...")
        self.add_cond_btn.clicked.connect(self.on_add_condition)
        self.edit_cond_btn = QPushButton("Editar Seleccionada...")
        self.edit_cond_btn.clicked.connect(self.on_edit_condition)
        self.del_cond_btn = QPushButton("Eliminar Condición")
        self.del_cond_btn.clicked.connect(self.on_delete_condition)
        btn_cond_layout.addWidget(self.add_cond_btn)
        btn_cond_layout.addWidget(self.edit_cond_btn)
        btn_cond_layout.addWidget(self.del_cond_btn)
        cond_layout.addLayout(btn_cond_layout)

        self.tab_widget.addTab(tab_conds, "2. Condiciones (1..N)")

        # =====================================================================
        # PESTAÑA 3: Repetición y Efectos
        # =====================================================================
        tab_effects = QWidget()
        eff_layout = QVBoxLayout(tab_effects)

        # Repetición y salida
        loop_group = QGroupBox("Ciclo de Repetición (Permanecer en Active)")
        loop_vbox = QVBoxLayout(loop_group)
        self.repeatable_check = QCheckBox("Repetir LoreBlock (no pasar a Done automáticamente)")
        self.repeatable_check.toggled.connect(self.on_repeatable_toggled)
        loop_vbox.addWidget(self.repeatable_check)

        self.exit_label = QLabel("Condiciones de salida para transicionar a Done:")
        loop_vbox.addWidget(self.exit_label)

        self.exit_table = QTableWidget(0, 5)
        self.exit_table.setHorizontalHeaderLabels(["Negado", "Tipo", "Entidad", "Condición", "Valor"])
        self.exit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.exit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.exit_table.setSelectionMode(QTableWidget.SingleSelection)
        self.exit_table.doubleClicked.connect(self.on_edit_exit_condition)
        self.exit_table.setMaximumHeight(90)
        loop_vbox.addWidget(self.exit_table)

        btn_exit_layout = QHBoxLayout()
        self.add_exit_btn = QPushButton("Añadir Salida...")
        self.add_exit_btn.clicked.connect(self.on_add_exit_condition)
        self.edit_exit_btn = QPushButton("Editar Salida...")
        self.edit_exit_btn.clicked.connect(self.on_edit_exit_condition)
        self.del_exit_btn = QPushButton("Eliminar Salida")
        self.del_exit_btn.clicked.connect(self.on_delete_exit_condition)
        btn_exit_layout.addWidget(self.add_exit_btn)
        btn_exit_layout.addWidget(self.edit_exit_btn)
        btn_exit_layout.addWidget(self.del_exit_btn)
        loop_vbox.addLayout(btn_exit_layout)
        eff_layout.addWidget(loop_group)

        # Efectos
        eff_group = QGroupBox("Efectos al Estado de Juego")
        eff_form = QFormLayout(eff_group)

        self.timing_combo = QComboBox()
        self.timing_combo.addItem("Al activarse el bloque (on_active)", "on_active")
        self.timing_combo.addItem("Al completarse y pasar a Done (on_done)", "on_done")
        eff_form.addRow("Momento de Aplicación:", self.timing_combo)

        eff_row1 = QHBoxLayout()
        self.gold_delta_spin = QSpinBox()
        self.gold_delta_spin.setRange(-99999, 99999)
        self.affinity_delta_spin = QDoubleSpinBox()
        self.affinity_delta_spin.setRange(-1.0, 1.0)
        self.affinity_delta_spin.setSingleStep(0.05)
        eff_row1.addWidget(QLabel("Oro (+/-):"))
        eff_row1.addWidget(self.gold_delta_spin)
        eff_row1.addWidget(QLabel("Afinidad (+/-):"))
        eff_row1.addWidget(self.affinity_delta_spin)
        eff_form.addRow(eff_row1)

        self.give_items_edit = QLineEdit()
        self.give_items_edit.setPlaceholderText("ID de objetos separados por comas...")
        eff_form.addRow("Entregar Objetos:", self.give_items_edit)

        self.take_items_edit = QLineEdit()
        self.take_items_edit.setPlaceholderText("ID de objetos a retirar...")
        eff_form.addRow("Retirar Objetos:", self.take_items_edit)

        self.unlock_places_edit = QLineEdit()
        self.unlock_places_edit.setPlaceholderText("ID o nombre de lugares a descubrir...")
        eff_form.addRow("Lugares Descubiertos:", self.unlock_places_edit)

        self.unlock_npcs_edit = QLineEdit()
        self.unlock_npcs_edit.setPlaceholderText("ID o nombre de NPCs conocidos...")
        eff_form.addRow("NPCs Conocidos:", self.unlock_npcs_edit)

        eff_layout.addWidget(eff_group)
        self.tab_widget.addTab(tab_effects, "3. Repetición y Efectos")

        main_layout.addWidget(self.tab_widget)

        # Botones Aceptar / Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Poblar lista de entidades candidatas y carpetas padre
        self.populate_target_entities()
        self.populate_parent_combo(lore_block.id if lore_block else None)
        if initial_parent_id:
            idx_p = self.parent_combo.findData(initial_parent_id)
            if idx_p >= 0:
                self.parent_combo.setCurrentIndex(idx_p)

        self.on_repeatable_toggled(False)

        if lore_block:
            self.set_data(lore_block)

    def populate_parent_combo(self, current_block_id: Optional[str] = None):
        """Puebla el selector de carpeta/bloque padre evitando ciclos recursivos."""
        self.parent_combo.clear()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")

        if not self.controller:
            return

        all_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])

        # Para prevenir ciclos recursivos, excluir al bloque actual y a sus descendientes
        forbidden_ids = set()
        if current_block_id:
            forbidden_ids.add(current_block_id)
            changed = True
            while changed:
                changed = False
                for b in all_blocks:
                    if b.id not in forbidden_ids and getattr(b, "parent_id", None) in forbidden_ids:
                        forbidden_ids.add(b.id)
                        changed = True

        for b in all_blocks:
            if b.id in forbidden_ids:
                continue
            title = b.title or b.name or b.id
            self.parent_combo.addItem(f"📁 {title} ({b.id})", b.id)

    def populate_target_entities(self):
        """Puebla la lista de entidades candidatas (NPCs, Lugares, Objetos) con checkboxes."""
        self.target_list.blockSignals(True)
        self.target_list.clear()

        if not self.controller:
            self.target_list.blockSignals(False)
            return

        # 1. NPCs
        for n in self.controller.get_npcs():
            item = QListWidgetItem(f"[NPC] {n.name} ({n.id})")
            item.setData(Qt.UserRole, n.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.target_list.addItem(item)

        # 2. Lugares
        for p in self.controller.get_all_places():
            item = QListWidgetItem(f"[Lugar] {p.name} ({p.id})")
            item.setData(Qt.UserRole, p.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.target_list.addItem(item)

        # 3. Objetos
        objects = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
        for obj in objects:
            item = QListWidgetItem(f"[Objeto] {obj.name} ({obj.id})")
            item.setData(Qt.UserRole, obj.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.target_list.addItem(item)

        self.target_list.blockSignals(False)

    def filter_target_entities(self, query: str):
        q = query.strip().lower()
        for i in range(self.target_list.count()):
            item = self.target_list.item(i)
            matches = (q in item.text().lower()) or (q in str(item.data(Qt.UserRole)).lower())
            item.setHidden(not matches)

    def on_target_selection_changed(self, _item):
        selected = self.get_selected_target_entities()
        if selected:
            self.target_summary_label.setText(f"Afecta a ({len(selected)}): {', '.join(selected)}")
        else:
            self.target_summary_label.setText("Afecta a: (Ninguna entidad seleccionada)")

    def get_selected_target_entities(self) -> List[str]:
        res = []
        for i in range(self.target_list.count()):
            it = self.target_list.item(i)
            if it.checkState() == Qt.Checked:
                res.append(it.data(Qt.UserRole))
        return res

    def on_rag_toggled(self, checked: bool):
        self.phrases_edit.setEnabled(checked)

    def on_repeatable_toggled(self, checked: bool):
        self.exit_label.setEnabled(checked)
        self.exit_table.setEnabled(checked)
        self.add_exit_btn.setEnabled(checked)
        self.edit_exit_btn.setEnabled(checked)
        self.del_exit_btn.setEnabled(checked)

    # --- TABLA DE CONDICIONES DE ACTIVACIÓN ---

    def populate_conditions_table(self):
        self.cond_table.setRowCount(0)
        for cond in self.conditions:
            row = self.cond_table.rowCount()
            self.cond_table.insertRow(row)
            self.cond_table.setItem(row, 0, QTableWidgetItem("NOT" if cond.is_negated else "NORMAL"))
            self.cond_table.setItem(row, 1, QTableWidgetItem(cond.entity_type.upper()))
            self.cond_table.setItem(row, 2, QTableWidgetItem(cond.entity_id))
            self.cond_table.setItem(row, 3, QTableWidgetItem(cond.sub_condition))
            self.cond_table.setItem(row, 4, QTableWidgetItem(str(cond.value) if cond.value is not None else "-"))

    def on_add_condition(self):
        dialog = ConditionDialog(controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.conditions.append(dialog.get_data())
            self.populate_conditions_table()

    def on_edit_condition(self):
        row = self.cond_table.currentRow()
        if row < 0 or row >= len(self.conditions):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una condición para editar.")
            return
        cond = self.conditions[row]
        dialog = ConditionDialog(condition=cond, controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.conditions[row] = dialog.get_data()
            self.populate_conditions_table()

    def on_delete_condition(self):
        row = self.cond_table.currentRow()
        if row < 0 or row >= len(self.conditions):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una condición para eliminar.")
            return
        self.conditions.pop(row)
        self.populate_conditions_table()

    # --- TABLA DE CONDICIONES DE SALIDA ---

    def populate_exit_table(self):
        self.exit_table.setRowCount(0)
        for cond in self.exit_conditions:
            row = self.exit_table.rowCount()
            self.exit_table.insertRow(row)
            self.exit_table.setItem(row, 0, QTableWidgetItem("NOT" if cond.is_negated else "NORMAL"))
            self.exit_table.setItem(row, 1, QTableWidgetItem(cond.entity_type.upper()))
            self.exit_table.setItem(row, 2, QTableWidgetItem(cond.entity_id))
            self.exit_table.setItem(row, 3, QTableWidgetItem(cond.sub_condition))
            self.exit_table.setItem(row, 4, QTableWidgetItem(str(cond.value) if cond.value is not None else "-"))

    def on_add_exit_condition(self):
        dialog = ConditionDialog(controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.exit_conditions.append(dialog.get_data())
            self.populate_exit_table()

    def on_edit_exit_condition(self):
        row = self.exit_table.currentRow()
        if row < 0 or row >= len(self.exit_conditions):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una condición para editar.")
            return
        cond = self.exit_conditions[row]
        dialog = ConditionDialog(condition=cond, controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.exit_conditions[row] = dialog.get_data()
            self.populate_exit_table()

    def on_delete_exit_condition(self):
        row = self.exit_table.currentRow()
        if row < 0 or row >= len(self.exit_conditions):
            QMessageBox.information(self, "Selección", "Por favor, selecciona una condición para eliminar.")
            return
        self.exit_conditions.pop(row)
        self.populate_exit_table()

    # --- CARGA Y DESCARGA DE DATOS ---

    def set_data(self, block: LoreBlock):
        self.id_edit.setText(block.id)
        self.title_edit.setText(block.title or "")

        # Carpeta / Bloque Padre HSM
        self.populate_parent_combo(block.id)
        if getattr(block, "parent_id", None):
            idx_p = self.parent_combo.findData(block.parent_id)
            if idx_p >= 0:
                self.parent_combo.setCurrentIndex(idx_p)
            else:
                self.parent_combo.addItem(f"📁 {block.parent_id} [Externo]", block.parent_id)
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
        else:
            self.parent_combo.setCurrentIndex(0)

        idx_st = self.state_combo.findData(block.state)
        if idx_st >= 0:
            self.state_combo.setCurrentIndex(idx_st)

        idx_m = self.mode_combo.findData(block.trigger_mode)
        if idx_m >= 0:
            self.mode_combo.setCurrentIndex(idx_m)

        self.rag_check.setChecked(block.rag_enabled)
        self.phrases_edit.setPlainText("\n".join(block.trigger_phrases))
        self.directive_edit.setPlainText(block.directive)

        # Entidades objetivo (target_entities)
        targets = set(getattr(block, "target_entities", []) or [])
        self.target_list.blockSignals(True)
        for i in range(self.target_list.count()):
            it = self.target_list.item(i)
            eid = it.data(Qt.UserRole)
            if eid in targets:
                it.setCheckState(Qt.Checked)
            else:
                it.setCheckState(Qt.Unchecked)
        self.target_list.blockSignals(False)
        self.on_target_selection_changed(None)

        # Condiciones
        self.conditions = list(block.conditions)
        self.populate_conditions_table()

        # Repetición y Salida
        self.repeatable_check.setChecked(block.repeatable)
        self.exit_conditions = list(block.exit_conditions)
        self.populate_exit_table()

        # Efectos
        idx_t = self.timing_combo.findData(block.effect_timing)
        if idx_t >= 0:
            self.timing_combo.setCurrentIndex(idx_t)

        self.give_items_edit.setText(", ".join(block.effects.give_items))
        self.take_items_edit.setText(", ".join(block.effects.take_items))

        delta = block.effects.gold_delta if block.effects.gold_delta != 0 else (block.effects.give_gold - block.effects.take_gold)
        self.gold_delta_spin.setValue(delta)
        self.affinity_delta_spin.setValue(block.effects.affinity_delta)

        self.unlock_places_edit.setText(", ".join(block.effects.unlock_places))
        self.unlock_npcs_edit.setText(", ".join(block.effects.unlock_npcs))

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
        give_items = [i.strip() for i in self.give_items_edit.text().split(",") if i.strip()]
        take_items = [i.strip() for i in self.take_items_edit.text().split(",") if i.strip()]
        unlock_places = [p.strip() for p in self.unlock_places_edit.text().split(",") if p.strip()]
        unlock_npcs = [n.strip() for n in self.unlock_npcs_edit.text().split(",") if n.strip()]

        gold_delta = self.gold_delta_spin.value()
        give_gold = gold_delta if gold_delta > 0 else 0
        take_gold = abs(gold_delta) if gold_delta < 0 else 0

        effects = LoreEffects(
            give_items=give_items,
            take_items=take_items,
            give_gold=give_gold,
            take_gold=take_gold,
            gold_delta=gold_delta,
            affinity_delta=self.affinity_delta_spin.value(),
            unlock_places=unlock_places,
            unlock_npcs=unlock_npcs,
        )

        selected_targets = self.get_selected_target_entities()

        parent_val = self.parent_combo.currentData()
        parent_id = str(parent_val).strip() if parent_val and str(parent_val).strip() else None

        return LoreBlock(
            id=self.id_edit.text().strip(),
            title=self.title_edit.text().strip() or None,
            parent_id=parent_id,
            state=self.state_combo.currentData(),
            rag_enabled=self.rag_check.isChecked(),
            trigger_mode=self.mode_combo.currentData(),
            trigger_phrases=phrases,
            target_entities=selected_targets,
            directive=self.directive_edit.toPlainText().strip(),
            conditions=self.conditions,
            repeatable=self.repeatable_check.isChecked(),
            exit_conditions=self.exit_conditions,
            effect_timing=self.timing_combo.currentData(),
            effects=effects,
        )


class LoreBlockTreeWidget(QWidget):
    """Widget de explorador jerárquico tipo árbol (HSM / Carpetas de Archivos) para gestionar LoreBlocks."""

    lore_changed = Signal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.lore_blocks: List[LoreBlock] = []

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels([
            "Jerarquía de LoreBlocks (Carpetas / Archivos)",
            "Afecta a (Entidades)",
            "Estado HSM",
            "Modo",
            "Condiciones / Salida",
            "RAG",
        ])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tree.itemDoubleClicked.connect(self.on_edit_block)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.add_root_btn = QPushButton("➕ Añadir Bloque Raíz...")
        self.add_root_btn.clicked.connect(self.on_add_root_block)

        self.add_child_btn = QPushButton("📁➕ Añadir Sub-bloque...")
        self.add_child_btn.clicked.connect(self.on_add_child_block)

        self.edit_btn = QPushButton("✏️ Editar...")
        self.edit_btn.clicked.connect(self.on_edit_block)

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.clicked.connect(self.on_delete_block)

        btn_layout.addWidget(self.add_root_btn)
        btn_layout.addWidget(self.add_child_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)

    def set_controller(self, controller):
        self.controller = controller

    def set_lore_blocks(self, lore_blocks: List[LoreBlock]):
        self.lore_blocks = lore_blocks or []
        self.populate_tree()

    def get_lore_blocks(self) -> List[LoreBlock]:
        return self.lore_blocks

    def populate_tree(self):
        self.tree.clear()
        if not self.lore_blocks:
            return

        id_to_block = {b.id: b for b in self.lore_blocks}
        parent_to_children = {}
        for b in self.lore_blocks:
            p_id = getattr(b, "parent_id", None)
            if p_id and p_id in id_to_block:
                parent_to_children.setdefault(p_id, []).append(b)

        roots = [b for b in self.lore_blocks if not b.parent_id or b.parent_id not in id_to_block]

        def create_tree_item(parent_widget, block: LoreBlock):
            item = QTreeWidgetItem(parent_widget)
            item.setData(0, Qt.UserRole, block.id)

            has_children = block.id in parent_to_children and bool(parent_to_children[block.id])

            if has_children:
                icon_prefix = "📂 " if block.state == "active" else "📁 "
            else:
                icon_prefix = "📜 "

            title = block.title or (block.directive[:35] + "..." if len(block.directive) > 35 else block.directive)
            item.setText(0, f"{icon_prefix}{title}  ({block.id})")

            # Columna 1: Afecta a
            targets = getattr(block, "target_entities", []) or []
            item.setText(1, ", ".join(targets) if targets else "(Ninguna)")

            # Columna 2: Estado HSM
            st = block.state.upper()
            if st == "ACTIVE":
                item.setText(2, "🟢 ACTIVO (Abierto)")
                item.setForeground(2, Qt.darkGreen)
            elif st == "DONE":
                item.setText(2, "🔵 RESUELTO")
                item.setForeground(2, Qt.blue)
            else:
                item.setText(2, "⚪ UNKNOWN")
                item.setForeground(2, Qt.darkGray)

            # Columna 3: Modo
            item.setText(3, block.trigger_mode.capitalize())

            # Columna 4: Condiciones
            c_info = f"{len(block.conditions)} act."
            if block.exit_conditions:
                c_info += f" / {len(block.exit_conditions)} sal."
            item.setText(4, c_info)

            # Columna 5: RAG
            item.setText(5, "Sí" if block.rag_enabled else "No")

            for child in parent_to_children.get(block.id, []):
                create_tree_item(item, child)

            return item

        for r in roots:
            create_tree_item(self.tree, r)

        self.tree.expandAll()

    def get_selected_block(self) -> Optional[LoreBlock]:
        item = self.tree.currentItem()
        if not item:
            return None
        b_id = item.data(0, Qt.UserRole)
        for b in self.lore_blocks:
            if b.id == b_id:
                return b
        return None

    def on_add_root_block(self):
        dialog = LoreBlockDialog(controller=self.controller, initial_parent_id=None, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_block = dialog.get_data()
            self.lore_blocks.append(new_block)
            self.populate_tree()
            self.lore_changed.emit()

    def on_add_child_block(self):
        selected = self.get_selected_block()
        parent_id = selected.id if selected else None
        dialog = LoreBlockDialog(controller=self.controller, initial_parent_id=parent_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_block = dialog.get_data()
            self.lore_blocks.append(new_block)
            self.populate_tree()
            self.lore_changed.emit()

    def on_edit_block(self):
        selected = self.get_selected_block()
        if not selected:
            QMessageBox.information(self, "Selección", "Por favor, selecciona un bloque en el árbol para editar.")
            return

        dialog = LoreBlockDialog(lore_block=selected, controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_block = dialog.get_data()
            idx = next((i for i, b in enumerate(self.lore_blocks) if b.id == selected.id), -1)
            if idx >= 0:
                self.lore_blocks[idx] = updated_block
            self.populate_tree()
            self.lore_changed.emit()

    def on_delete_block(self):
        selected = self.get_selected_block()
        if not selected:
            QMessageBox.information(self, "Selección", "Por favor, selecciona un bloque para eliminar.")
            return

        children = [b for b in self.lore_blocks if getattr(b, "parent_id", None) == selected.id]
        if children:
            res = QMessageBox.question(
                self, "Eliminar LoreBlock Contenedor",
                f"El bloque '{selected.id}' contiene {len(children)} sub-bloque(s).\n\n"
                "¿Deseas eliminarlo JUNTO con todos sus sub-bloques en cascada?\n\n"
                "(Si eliges 'No', los sub-bloques se promoverán al nivel superior/raíz)",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if res == QMessageBox.Cancel:
                return
            elif res == QMessageBox.Yes:
                ids_to_del = {selected.id}
                changed = True
                while changed:
                    changed = False
                    for b in self.lore_blocks:
                        if b.id not in ids_to_del and getattr(b, "parent_id", None) in ids_to_del:
                            ids_to_del.add(b.id)
                            changed = True
                self.lore_blocks = [b for b in self.lore_blocks if b.id not in ids_to_del]
            else:
                for c in children:
                    c.parent_id = selected.parent_id
                self.lore_blocks = [b for b in self.lore_blocks if b.id != selected.id]
        else:
            confirm = QMessageBox.question(
                self, "Eliminar Lore",
                f"¿Estás seguro de eliminar el bloque '{selected.id}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            self.lore_blocks = [b for b in self.lore_blocks if b.id != selected.id]

        self.populate_tree()
        self.lore_changed.emit()


# Alias para mantener compatibilidad total con vistas y formularios existentes
LoreBlockTableWidget = LoreBlockTreeWidget
