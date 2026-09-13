"""Diálogo universal y contextual para seleccionar entidades del juego (Lugares, NPCs, Objetos, LoreBlocks).

Utiliza emojis visuales:
- 📍 Lugar (Place)
- 👤 Personaje (NPC)
- 📦 Objeto (Item)
- 📜 Bloque de Lore (LoreBlock)
"""

from typing import List, Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDoubleSpinBox, QCheckBox, QDialogButtonBox, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from domains.lore import EntityCondition


class EntityPickerDialog(QDialog):
    """
    Diálogo modal reutilizable para seleccionar entidades o configurar condiciones sobre ellas.
    
    Parámetros:
        controller: Controlador con acceso al mundo, npcs, objetos y lore.
        allowed_types: Lista de tipos permitidos, e.g. ["place", "npc", "item", "loreblock"] o ["npc", "item"].
        mode: "condition" (configura una EntityCondition completa) o "entity_only" (retorna solo ID de entidad).
        initial_condition: EntityCondition existente para pre-rellenar (en modo condition).
        initial_entity_id: ID existente para pre-seleccionar (en modo entity_only).
    """

    TYPE_EMOJIS = {
        "place": "📍",
        "npc": "👤",
        "item": "📦",
        "loreblock": "📜",
    }

    TYPE_LABELS = {
        "place": "📍 Lugar (Place)",
        "npc": "👤 Personaje (NPC)",
        "item": "📦 Objeto (Item)",
        "loreblock": "📜 Bloque de Lore (HSM)",
    }

    def __init__(
        self,
        controller,
        allowed_types: Optional[List[str]] = None,
        mode: str = "condition",
        initial_condition: Optional[EntityCondition] = None,
        initial_entity_id: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.allowed_types = allowed_types or ["place", "npc", "item", "loreblock"]
        self.mode = mode
        self.initial_condition = initial_condition
        self.initial_entity_id = initial_entity_id

        title = "Configurar Condición de Entidad" if self.mode == "condition" else "Seleccionar Entidad"
        self.setWindowTitle(title)
        self.resize(480, 420)

        main_layout = QVBoxLayout(self)

        # 1. Selector de Tipo de Entidad (solo si hay más de un tipo permitido)
        if len(self.allowed_types) > 1:
            type_box = QHBoxLayout()
            type_box.addWidget(QLabel("Tipo de Entidad:"))
            self.type_combo = QComboBox()
            for t in self.allowed_types:
                label = self.TYPE_LABELS.get(t, t.capitalize())
                self.type_combo.addItem(label, t)
            self.type_combo.currentIndexChanged.connect(self.on_type_changed)
            type_box.addWidget(self.type_combo)
            main_layout.addLayout(type_box)
        else:
            self.type_combo = None

        # 2. Buscador de texto
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Escribe para filtrar por nombre o ID...")
        self.search_edit.textChanged.connect(self.filter_entities)
        search_box.addWidget(self.search_edit)
        main_layout.addLayout(search_box)

        # 3. Lista de entidades seleccionables
        self.entity_list = QListWidget()
        self.entity_list.itemSelectionChanged.connect(self.on_entity_selected)
        main_layout.addWidget(self.entity_list)

        # 4. Formulario de subcondición (solo en modo condition)
        if self.mode == "condition":
            cond_group = QGroupBox("Parámetros de la Condición")
            cond_layout = QFormLayout(cond_group)

            self.sub_combo = QComboBox()
            self.sub_combo.currentIndexChanged.connect(self.on_sub_changed)
            cond_layout.addRow("Subcondición:", self.sub_combo)

            self.value_spin = QDoubleSpinBox()
            self.value_spin.setRange(0.0, 99999.0)
            self.value_spin.setSingleStep(0.05)
            self.value_row_label = QLabel("Valor Requerido:")
            cond_layout.addRow(self.value_row_label, self.value_spin)

            self.negated_check = QCheckBox("Invertir / Negar condición (NOT)")
            cond_layout.addRow(self.negated_check)

            main_layout.addWidget(cond_group)

        # 5. Botones Aceptar / Cancelar
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.on_accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

        # Cargar entidades
        self.populate_entities()

        # Preseleccionar valores iniciales si los hay
        if self.initial_condition and self.mode == "condition":
            self.set_from_condition(self.initial_condition)
        elif self.initial_entity_id:
            self.set_from_entity_id(self.initial_entity_id)

    def current_entity_type(self) -> str:
        if self.type_combo:
            return self.type_combo.currentData()
        return self.allowed_types[0]

    def on_type_changed(self):
        self.populate_entities()
        if self.mode == "condition":
            self.populate_subconditions()

    def populate_entities(self):
        self.entity_list.clear()
        etype = self.current_entity_type()
        emoji = self.TYPE_EMOJIS.get(etype, "🔹")

        if not self.controller:
            return

        if etype == "place":
            places = self.controller.get_all_places()
            for p in places:
                item = QListWidgetItem(f"{emoji} {p.name} ({p.id})")
                item.setData(Qt.UserRole, p.id)
                item.setData(Qt.UserRole + 1, p.name)
                self.entity_list.addItem(item)

        elif etype == "npc":
            for n in self.controller.get_npcs():
                item = QListWidgetItem(f"{emoji} {n.name} ({n.id})")
                item.setData(Qt.UserRole, n.id)
                item.setData(Qt.UserRole + 1, n.name)
                self.entity_list.addItem(item)

        elif etype == "item":
            if self.mode == "condition":
                gold_item = QListWidgetItem(f"💰 Monedas de Oro (gold)")
                gold_item.setData(Qt.UserRole, "gold")
                gold_item.setData(Qt.UserRole + 1, "Oro")
                self.entity_list.addItem(gold_item)

            objects = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
            for obj in objects:
                item = QListWidgetItem(f"{emoji} {obj.name} ({obj.id})")
                item.setData(Qt.UserRole, obj.id)
                item.setData(Qt.UserRole + 1, obj.name)
                self.entity_list.addItem(item)

        elif etype == "loreblock":
            lore_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])
            for b in lore_blocks:
                title = b.title or b.name or b.id
                icon = "📁" if getattr(b, "parent_id", None) else emoji
                item = QListWidgetItem(f"{icon} {title} ({b.id})")
                item.setData(Qt.UserRole, b.id)
                item.setData(Qt.UserRole + 1, title)
                self.entity_list.addItem(item)

        if self.entity_list.count() > 0:
            self.entity_list.setCurrentRow(0)

        if self.mode == "condition":
            self.populate_subconditions()

    def filter_entities(self, text: str):
        q = text.strip().lower()
        for i in range(self.entity_list.count()):
            it = self.entity_list.item(i)
            match = (q in it.text().lower()) or (q in str(it.data(Qt.UserRole)).lower())
            it.setHidden(not match)

    def populate_subconditions(self):
        etype = self.current_entity_type()
        self.sub_combo.clear()

        if etype == "place":
            self.sub_combo.addItem("known (A la vista / Descubierto)", "known")
            self.sub_combo.addItem("current_location (Ubicación actual del jugador)", "current_location")
        elif etype == "npc":
            self.sub_combo.addItem("known (Conocido por el jugador)", "known")
            self.sub_combo.addItem("affinity (Nivel mínimo de afinidad)", "affinity")
        elif etype == "item":
            self.sub_combo.addItem("have (En el inventario del jugador)", "have")
            self.sub_combo.addItem("known (Conocido / Visto por el jugador)", "known")
        elif etype == "loreblock":
            self.sub_combo.addItem("done (En estado Done / Completado)", "done")
            self.sub_combo.addItem("active (En estado Activo)", "active")
            self.sub_combo.addItem("any_child_done (Cualquier sub-bloque completado)", "any_child_done")

        self.on_sub_changed()

    def on_entity_selected(self):
        if self.mode == "condition":
            self.on_sub_changed()

    def on_sub_changed(self):
        if self.mode != "condition":
            return
        sub = self.sub_combo.currentData()
        etype = self.current_entity_type()
        selected_item = self.entity_list.currentItem()
        ent_id = selected_item.data(Qt.UserRole) if selected_item else ""

        is_affinity = (sub == "affinity")
        is_gold = (etype == "item" and ent_id == "gold")
        show_value = is_affinity or is_gold

        if is_affinity:
            self.value_spin.setRange(0.0, 1.0)
            self.value_spin.setDecimals(2)
            self.value_spin.setSingleStep(0.05)
            self.value_row_label.setText("Afinidad Requerida (0.0 - 1.0):")
        elif is_gold:
            self.value_spin.setRange(0.0, 99999.0)
            self.value_spin.setDecimals(0)
            self.value_spin.setSingleStep(10.0)
            self.value_row_label.setText("Cantidad de Oro:")

        self.value_spin.setVisible(show_value)
        self.value_row_label.setVisible(show_value)

    def on_accept(self):
        item = self.entity_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona una entidad de la lista.")
            return
        self.accept()

    def get_selected_entity_id(self) -> str:
        item = self.entity_list.currentItem()
        return str(item.data(Qt.UserRole)) if item else ""

    def get_selected_entity_name(self) -> str:
        item = self.entity_list.currentItem()
        return str(item.data(Qt.UserRole + 1)) if item else ""

    def get_selected_entity_type(self) -> str:
        return self.current_entity_type()

    def get_condition(self) -> EntityCondition:
        etype = self.current_entity_type()
        ent_id = self.get_selected_entity_id()
        sub = self.sub_combo.currentData()
        val = None
        if sub == "affinity" or (etype == "item" and ent_id == "gold"):
            val = self.value_spin.value()

        return EntityCondition(
            entity_type=etype,
            entity_id=ent_id,
            sub_condition=sub,
            value=val,
            is_negated=self.negated_check.isChecked(),
        )

    def set_from_condition(self, cond: EntityCondition):
        if self.type_combo:
            idx = self.type_combo.findData(cond.entity_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        # Buscar y seleccionar la entidad
        for i in range(self.entity_list.count()):
            it = self.entity_list.item(i)
            if it.data(Qt.UserRole) == cond.entity_id:
                self.entity_list.setCurrentItem(it)
                break

        # Subcondición
        idx_sub = self.sub_combo.findData(cond.sub_condition)
        if idx_sub >= 0:
            self.sub_combo.setCurrentIndex(idx_sub)

        # Valor
        if cond.value is not None:
            self.value_spin.setValue(float(cond.value))

        # Negación
        self.negated_check.setChecked(cond.is_negated)

    def set_from_entity_id(self, ent_id: str):
        for i in range(self.entity_list.count()):
            it = self.entity_list.item(i)
            if it.data(Qt.UserRole) == ent_id:
                self.entity_list.setCurrentItem(it)
                break
