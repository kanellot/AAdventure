"""Formulario unificado para la edición de Bloques de Lore (HSM).

Estructura canónica:
1. Información del Bloque: ID, Nombre/Título, Tipo (Chapter, Quest, Task, Event), Padre HSM y Descripción.
2. Condiciones estructuradas:
   - active_conditions: Lista de requisitos lógicos y antenas RAG para pasar de unknown a active.
   - done_conditions: Lista de requisitos lógicos y antenas RAG para pasar de active a done.
3. Efectos sobre entidades (solo activos):
   - Tipo de acción (hook / push), tiempo transcurrido (HH:MM), directiva, bypass LLM,
     oro, afinidad, inventario (dar/quitar), revelar entidades (lugares, npcs, objetos)
     y conexiones bloqueadas.
   - Contenedores (Chapter, Quest, Task) actúan como nodos puros organizativos.
"""

from __future__ import annotations

from typing import Optional, List

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QPushButton, QScrollArea, QFrame,
    QDialog, QDialogButtonBox, QMenu, QMessageBox
)

from domains.lore import LoreBlock, LoreEffects, ConditionGroup
from editor_debugger.editor.constants import TYPE_METADATA
from editor_debugger.editor.views.compact_widgets import CompactConditionListWidget, CompactEntityListWidget
from editor_debugger.editor.views.entity_picker import EntityPickerDialog


class LoreEffectDialog(QDialog):
    """Diálogo modal para crear o editar un efecto sobre una entidad en estado active."""

    def __init__(
            self,
            effect: Optional[LoreEffects] = None,
            controller=None,
            parent=None,
            is_popup: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configurar Efecto de Pop-up" if is_popup else "Configurar Efecto de Lore")
        self.resize(580, 680)
        self.controller = controller
        if effect:
            self.effect: LoreEffects = effect.model_copy(deep=True)
        else:
            self.effect: LoreEffects = LoreEffects(
                bypass_llm=True if is_popup else False,
                action="push" if is_popup else "hook",
            )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # 1. Objetivo / Target
        target_group = QGroupBox("Entidad Objetivo (Target)")
        target_form = QFormLayout(target_group)

        target_row = QHBoxLayout()
        self.target_combo = QComboBox()
        target_row.addWidget(self.target_combo, 1)

        self.pick_btn = QPushButton("🔍 Seleccionar...")
        self.pick_btn.setToolTip("Abrir diálogo de selección de entidades")
        self.pick_btn.setStyleSheet("padding: 3px 8px; font-weight: bold;")
        self.pick_btn.clicked.connect(self.on_pick_target)
        target_row.addWidget(self.pick_btn)

        target_form.addRow("Entidad Objetivo:", target_row)
        layout.addWidget(target_group)

        # 2. Acción y Tiempo de Juego
        action_group = QGroupBox("Comportamiento y Tiempo de Ejecución")
        action_form = QFormLayout(action_group)

        self.action_combo = QComboBox()
        self.action_combo.addItem("🎧 Hook (Acción pasiva / Se inyecta contexto al interactuar con la entidad)", "hook")
        self.action_combo.addItem("⚡ Push (Acción proactiva / Ejecución forzada inmediata del loreblock)", "push")
        action_form.addRow("Tipo de Acción:", self.action_combo)

        time_row = QHBoxLayout()
        self.time_hours_spin = QSpinBox()
        self.time_hours_spin.setRange(0, 99)
        self.time_hours_spin.setSuffix(" h")
        self.time_mins_spin = QSpinBox()
        self.time_mins_spin.setRange(0, 59)
        self.time_mins_spin.setSuffix(" min")
        time_row.addWidget(QLabel("Horas:"))
        time_row.addWidget(self.time_hours_spin)
        time_row.addWidget(QLabel("Minutos:"))
        time_row.addWidget(self.time_mins_spin)
        time_row.addStretch()
        action_form.addRow("⏳ Tiempo Sumado (HH:MM):", time_row)

        layout.addWidget(action_group)

        # 3. Directiva y Bypass de LLM
        dir_group = QGroupBox("Directiva Narrativa")
        dir_vbox = QVBoxLayout(dir_group)
        self.directive_edit = QTextEdit()
        self.directive_edit.setPlaceholderText("Instrucción narrativa inyectada o texto exacto para el jugador...")
        self.directive_edit.setMaximumHeight(80)
        dir_vbox.addWidget(self.directive_edit)

        self.bypass_llm_check = QCheckBox("⚡ Bypasear LLM (Respuesta directa exacta sin llamar a IA)")
        self.bypass_llm_check.setToolTip(
            "Si está marcado, la directiva se entrega textualmente al jugador sin consultar al LLM."
        )
        dir_vbox.addWidget(self.bypass_llm_check)
        layout.addWidget(dir_group)

        # 4. Mutaciones al Jugador (Oro y Afinidad)
        player_group = QGroupBox("Modificaciones de Jugador y Afinidad")
        player_form = QFormLayout(player_group)

        row_deltas = QHBoxLayout()
        self.gold_spin = QSpinBox()
        self.gold_spin.setRange(-99999, 99999)
        row_deltas.addWidget(QLabel("💰 Oro (+/-):"))
        row_deltas.addWidget(self.gold_spin)

        self.affinity_spin = QDoubleSpinBox()
        self.affinity_spin.setRange(-1.0, 1.0)
        self.affinity_spin.setSingleStep(0.05)
        row_deltas.addWidget(QLabel("❤️ Afinidad (+/-):"))
        row_deltas.addWidget(self.affinity_spin)
        player_form.addRow(row_deltas)
        layout.addWidget(player_group)

        # 5. Inventario del Jugador
        items_group = QGroupBox("Inventario del Jugador")
        items_layout = QHBoxLayout(items_group)

        give_vbox = QVBoxLayout()
        give_vbox.addWidget(QLabel("<b>🎁 Entregar al Jugador (give_items):</b>"))
        self.give_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Añadir Objeto...", parent=items_group
        )
        give_vbox.addWidget(self.give_items_widget)
        items_layout.addLayout(give_vbox)

        take_vbox = QVBoxLayout()
        take_vbox.addWidget(QLabel("<b>📤 Retirar del Jugador (take_items):</b>"))
        self.take_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Retirar Objeto...", parent=items_group
        )
        take_vbox.addWidget(self.take_items_widget)
        items_layout.addLayout(take_vbox)
        layout.addWidget(items_group)

        # 6. Revelación de Entidades (Visibilidad)
        unlock_group = QGroupBox("Entidades Reveladas al Jugador (Visibilidad)")
        unlock_layout = QVBoxLayout(unlock_group)

        self.unlock_places_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["place"], button_text="➕ Revelar Lugar...", parent=unlock_group
        )
        unlock_layout.addWidget(QLabel("<b>📍 Revelar Lugares (unlock_places):</b>"))
        unlock_layout.addWidget(self.unlock_places_widget)

        self.unlock_npcs_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["npc"], button_text="➕ Revelar Personaje...", parent=unlock_group
        )
        unlock_layout.addWidget(QLabel("<b>👤 Revelar Personajes (unlock_npcs):</b>"))
        unlock_layout.addWidget(self.unlock_npcs_widget)

        self.unlock_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Revelar Objeto...", parent=unlock_group
        )
        unlock_layout.addWidget(QLabel("<b>📦 Revelar Objetos (unlock_items):</b>"))
        unlock_layout.addWidget(self.unlock_items_widget)
        layout.addWidget(unlock_group)

        # 7. Control de Bloqueo / Desbloqueo de Lugares
        places_group = QGroupBox("Control de Acceso a Lugares (block_places / unblock_places)")
        places_layout = QVBoxLayout(places_group)

        self.block_places_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["place"], button_text="➕ Bloquear Lugar...", parent=places_group
        )
        places_layout.addWidget(QLabel("<b>🚫 Bloquear Lugares (block_places):</b>"))
        places_layout.addWidget(self.block_places_widget)

        self.unblock_places_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["place"], button_text="➕ Desbloquear Lugar...",
            parent=places_group
        )
        places_layout.addWidget(QLabel("<b>🔓 Desbloquear Lugares (unblock_places):</b>"))
        places_layout.addWidget(self.unblock_places_widget)
        layout.addWidget(places_group)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Botones inferiores OK / Cancelar
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("Guardar Efecto")
        btn_box.button(QDialogButtonBox.Cancel).setText("Cancelar")
        btn_box.accepted.connect(self.on_accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        self.populate_target_combo(self.effect.target)
        self.load_data(self.effect)

    def populate_target_combo(self, current_value: Optional[str] = None):
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("(Ninguno - Efecto Global / Sin Objetivo)", "")

        if self.controller:
            for n in self.controller.get_npcs():
                self.target_combo.addItem(f"👤 {n.name} ({n.id})", n.id)

            for p in self.controller.get_all_places():
                self.target_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

            for item in self.controller.get_items():
                self.target_combo.addItem(f"📦 {item.name} ({item.id})", item.id)

        if current_value:
            idx = self.target_combo.findData(current_value)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
            else:
                self.target_combo.addItem(f"🔹 {current_value} (Personalizado)", current_value)
                self.target_combo.setCurrentIndex(self.target_combo.count() - 1)
        else:
            self.target_combo.setCurrentIndex(0)

        self.target_combo.blockSignals(False)

    def load_data(self, eff: LoreEffects):
        self.directive_edit.setPlainText(eff.directive or "")
        self.bypass_llm_check.setChecked(eff.bypass_llm)

        act = getattr(eff, "action", "hook")
        idx_act = self.action_combo.findData(act)
        if idx_act >= 0:
            self.action_combo.setCurrentIndex(idx_act)

        # Elapsed time parsing (HH:MM)
        raw_time = getattr(eff, "elapsed_time", "00:00") or "00:00"
        parts = raw_time.split(":")
        h = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        m = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        self.time_hours_spin.setValue(h)
        self.time_mins_spin.setValue(m)

        self.gold_spin.setValue(eff.gold_delta)
        self.affinity_spin.setValue(eff.affinity_delta)

        self.give_items_widget.set_entity_ids(eff.give_items or [])
        self.take_items_widget.set_entity_ids(eff.take_items or [])
        self.unlock_places_widget.set_entity_ids(eff.unlock_places or [])
        self.unlock_npcs_widget.set_entity_ids(eff.unlock_npcs or [])
        self.unlock_items_widget.set_entity_ids(eff.unlock_items or [])
        self.block_places_widget.set_entity_ids(eff.block_places or [])
        self.unblock_places_widget.set_entity_ids(eff.unblock_places or [])

    def on_pick_target(self):
        current_target = self.target_combo.currentData() or ""
        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=["place", "npc", "item"],
            mode="entity_only",
            initial_entity_id=current_target,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = dialog.get_selected_entity_id()
            if selected_id:
                idx = self.target_combo.findData(selected_id)
                if idx >= 0:
                    self.target_combo.setCurrentIndex(idx)
                else:
                    selected_name = dialog.get_selected_entity_name() or selected_id
                    etype = dialog.get_selected_entity_type()
                    emoji = EntityPickerDialog.TYPE_EMOJIS.get(etype, "🔹")
                    self.target_combo.addItem(f"{emoji} {selected_name} ({selected_id})", selected_id)
                    self.target_combo.setCurrentIndex(self.target_combo.count() - 1)

    def _update_effect_from_ui(self):
        self.effect.target = self.target_combo.currentData() or None
        self.effect.directive = self.directive_edit.toPlainText().strip()
        self.effect.bypass_llm = self.bypass_llm_check.isChecked()
        self.effect.action = self.action_combo.currentData() or "hook"

        h = self.time_hours_spin.value()
        m = self.time_mins_spin.value()
        self.effect.elapsed_time = f"{h:02d}:{m:02d}"

        self.effect.gold_delta = self.gold_spin.value()
        self.effect.affinity_delta = self.affinity_spin.value()

        self.effect.give_items = self.give_items_widget.get_entity_ids()
        self.effect.take_items = self.take_items_widget.get_entity_ids()
        self.effect.unlock_places = self.unlock_places_widget.get_entity_ids()
        self.effect.unlock_npcs = self.unlock_npcs_widget.get_entity_ids()
        self.effect.unlock_items = self.unlock_items_widget.get_entity_ids()
        self.effect.block_places = self.block_places_widget.get_entity_ids()
        self.effect.unblock_places = self.unblock_places_widget.get_entity_ids()

    def on_accept(self):
        self._update_effect_from_ui()
        if self.effect.action == "hook" and not self.effect.target:
            QMessageBox.warning(
                self,
                "Validación de Efecto",
                "Las acciones de tipo Hook son pasivas y requieren obligatoriamente una Entidad Objetivo (target).\n\n"
                "Por favor, selecciona una entidad objetivo o cambia el tipo de acción a Push.",
            )
            return
        self.accept()

    def get_effect(self) -> LoreEffects:
        self._update_effect_from_ui()
        return self.effect


class LoreBlockForm(QWidget):
    """Formulario unificado para la edición completa del LoreBlock (HSM)."""

    lore_changed = Signal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.parent_app = parent
        self.lore_block: Optional[LoreBlock] = None
        self._loading = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Barra superior
        top_bar = QHBoxLayout()
        self.header_title = QLabel("<b>📜 Bloque de Lore (HSM)</b>")
        self.header_title.setStyleSheet("font-size: 14px; color: #5c6bc0;")
        top_bar.addWidget(self.header_title)
        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar este bloque de lore")
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

        # Área Scroleable Principal
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 4, 4, 4)
        self.container_layout.setSpacing(10)
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)

        # SECCIÓN 1: Información General
        self.info_group = QGroupBox("1. Información del Bloque")
        info_form = QFormLayout(self.info_group)
        info_form.setSpacing(6)

        self.type_combo = QComboBox()
        for type_key, meta in TYPE_METADATA.items():
            self.type_combo.addItem(f"{meta['icon']} {meta['label']}", type_key)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        info_form.addRow("Tipo de Bloque (Type):", self.type_combo)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("identificador_unico")
        self.id_edit.textChanged.connect(self.on_field_changed)
        info_form.addRow("ID Único:", self.id_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título descriptivo del secreto o misión...")
        self.title_edit.textChanged.connect(self.on_title_changed)
        info_form.addRow("Título:", self.title_edit)

        self.parent_combo = QComboBox()
        self.parent_combo.currentIndexChanged.connect(self.on_parent_changed)
        info_form.addRow("Bloque Padre (HSM):", self.parent_combo)

        self.desc_group = QWidget()
        desc_layout = QVBoxLayout(self.desc_group)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Descripción interna o contexto del bloque...")
        self.desc_edit.setMaximumHeight(65)
        self.desc_edit.textChanged.connect(self.on_field_changed)
        desc_layout.addWidget(self.desc_edit)
        info_form.addRow("Descripción:", self.desc_group)

        self.container_layout.addWidget(self.info_group)

        # SECCIÓN 2: Condiciones (active_conditions y done_conditions)
        self.conditions_group = QGroupBox("2. Condiciones (Active / Done)")
        cond_main_vbox = QVBoxLayout(self.conditions_group)
        cond_main_vbox.setSpacing(8)

        cond_header_layout = QHBoxLayout()
        cond_desc = QLabel(
            "Requisitos lógicos para pasar a <b>Active</b> y condiciones de salida para <b>Done</b>.<br>"
            "💡 <i>Haz doble clic sobre cualquier condición para editar sus parámetros.</i>"
        )
        cond_desc.setStyleSheet("color: #555; font-size: 11px;")
        cond_desc.setWordWrap(True)
        cond_header_layout.addWidget(cond_desc, 1)

        self.add_cond_btn = QPushButton("➕ Añadir Condición...")
        self.add_cond_btn.setStyleSheet("font-weight: bold; padding: 4px 10px;")
        self.add_cond_btn.clicked.connect(self.on_add_any_condition)
        cond_header_layout.addWidget(self.add_cond_btn)
        cond_main_vbox.addLayout(cond_header_layout)

        # 2.1: active_conditions
        self.active_box = QGroupBox("🟢 Requisitos para pasar a Active (active_conditions)")
        active_vbox = QVBoxLayout(self.active_box)
        active_vbox.setSpacing(4)
        active_vbox.setContentsMargins(6, 6, 6, 6)

        self.active_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=self.active_box)
        self.active_conditions_widget.conditions_changed.connect(self.on_active_conditions_changed)
        active_vbox.addWidget(self.active_conditions_widget)

        self.active_rag_box = QWidget()
        active_rag_vbox = QVBoxLayout(self.active_rag_box)
        active_rag_vbox.setContentsMargins(0, 2, 0, 0)
        active_rag_vbox.setSpacing(4)

        self.rag_active_check = QCheckBox("🎙️ Habilitar Antenas Semánticas RAG (rag_enabled)")
        self.rag_active_check.toggled.connect(self.on_rag_active_toggled)
        active_rag_vbox.addWidget(self.rag_active_check)

        self.phrases_active_edit = QTextEdit()
        self.phrases_active_edit.setPlaceholderText("Antenas RAG (trigger_phrases), una frase por línea...")
        self.phrases_active_edit.setMaximumHeight(55)
        self.phrases_active_edit.textChanged.connect(self.on_field_changed)
        self.phrases_active_edit.setVisible(False)
        active_rag_vbox.addWidget(self.phrases_active_edit)
        active_vbox.addWidget(self.active_rag_box)

        cond_main_vbox.addWidget(self.active_box)

        # 2.2: done_conditions
        self.done_box = QGroupBox("🔵 Condiciones de Salida para pasar a Done (done_conditions)")
        done_vbox = QVBoxLayout(self.done_box)
        done_vbox.setSpacing(4)
        done_vbox.setContentsMargins(6, 6, 6, 6)

        self.done_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=self.done_box)
        self.done_conditions_widget.conditions_changed.connect(self.on_done_conditions_changed)
        done_vbox.addWidget(self.done_conditions_widget)

        self.done_rag_box = QWidget()
        done_rag_vbox = QVBoxLayout(self.done_rag_box)
        done_rag_vbox.setContentsMargins(0, 2, 0, 0)
        done_rag_vbox.setSpacing(4)

        self.rag_done_check = QCheckBox("🎙️ Habilitar Antenas Semánticas RAG de Salida (rag_enabled)")
        self.rag_done_check.toggled.connect(self.on_rag_done_toggled)
        done_rag_vbox.addWidget(self.rag_done_check)

        self.phrases_done_edit = QTextEdit()
        self.phrases_done_edit.setPlaceholderText("Antenas RAG de salida (trigger_phrases), una frase por línea...")
        self.phrases_done_edit.setMaximumHeight(55)
        self.phrases_done_edit.textChanged.connect(self.on_field_changed)
        self.phrases_done_edit.setVisible(False)
        done_rag_vbox.addWidget(self.phrases_done_edit)
        done_vbox.addWidget(self.done_rag_box)

        cond_main_vbox.addWidget(self.done_box)
        self.container_layout.addWidget(self.conditions_group)

        # SECCIÓN 3: Efectos sobre Entidades (Doble Effect: active_effects y done_effects)
        self.effects_group = QGroupBox("3. Efectos sobre Entidades (Doble Effect)")
        eff_main_vbox = QVBoxLayout(self.effects_group)
        eff_main_vbox.setSpacing(10)

        # 3.1: active_effects
        self.active_effects_box = QGroupBox("🟢 Efectos al Activar (active_effects)")
        active_eff_vbox = QVBoxLayout(self.active_effects_box)
        active_eff_vbox.setSpacing(6)

        active_top_bar = QHBoxLayout()
        active_hint_lbl = QLabel("Se ejecutan cuando el bloque pasa de <b>unknown</b> a <b>active</b>.")
        active_hint_lbl.setStyleSheet("color: #555; font-size: 11px;")
        active_top_bar.addWidget(active_hint_lbl, 1)

        self.add_active_eff_btn = QPushButton("➕ Añadir Efecto al Activar...")
        self.add_active_eff_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.add_active_eff_btn.clicked.connect(self.on_add_active_effect_clicked)
        active_top_bar.addWidget(self.add_active_eff_btn)
        active_eff_vbox.addLayout(active_top_bar)

        self.active_effects_scroll = QScrollArea()
        self.active_effects_scroll.setWidgetResizable(True)
        self.active_effects_scroll.setMaximumHeight(180)
        self.active_effects_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")
        self.active_effects_container = QWidget()
        self.active_effects_container_layout = QVBoxLayout(self.active_effects_container)
        self.active_effects_container_layout.setContentsMargins(4, 4, 4, 4)
        self.active_effects_container_layout.setSpacing(4)
        self.active_effects_container_layout.setAlignment(Qt.AlignTop)
        self.active_effects_scroll.setWidget(self.active_effects_container)
        active_eff_vbox.addWidget(self.active_effects_scroll)

        eff_main_vbox.addWidget(self.active_effects_box)

        # 3.2: done_effects
        self.done_effects_box = QGroupBox("🔵 Efectos al Completar (done_effects)")
        done_eff_vbox = QVBoxLayout(self.done_effects_box)
        done_eff_vbox.setSpacing(6)

        done_top_bar = QHBoxLayout()
        done_hint_lbl = QLabel("Se ejecutan cuando el bloque pasa de <b>active</b> a <b>done</b>.")
        done_hint_lbl.setStyleSheet("color: #555; font-size: 11px;")
        done_top_bar.addWidget(done_hint_lbl, 1)

        self.add_done_eff_btn = QPushButton("➕ Añadir Efecto al Completar...")
        self.add_done_eff_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                color: white;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
        """)
        self.add_done_eff_btn.clicked.connect(self.on_add_done_effect_clicked)
        done_top_bar.addWidget(self.add_done_eff_btn)
        done_eff_vbox.addLayout(done_top_bar)

        self.done_effects_scroll = QScrollArea()
        self.done_effects_scroll.setWidgetResizable(True)
        self.done_effects_scroll.setMaximumHeight(180)
        self.done_effects_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")
        self.done_effects_container = QWidget()
        self.done_effects_container_layout = QVBoxLayout(self.done_effects_container)
        self.done_effects_container_layout.setContentsMargins(4, 4, 4, 4)
        self.done_effects_container_layout.setSpacing(4)
        self.done_effects_container_layout.setAlignment(Qt.AlignTop)
        self.done_effects_scroll.setWidget(self.done_effects_container)
        done_eff_vbox.addWidget(self.done_effects_scroll)

        eff_main_vbox.addWidget(self.done_effects_box)

        self.container_layout.addWidget(self.effects_group)
        self.container_layout.addStretch()

        self._apply_type_layout("Event")

    def set_controller(self, controller):
        self.controller = controller
        if hasattr(self, "active_conditions_widget"):
            self.active_conditions_widget.set_controller(controller)
            self.done_conditions_widget.set_controller(controller)
        self.refresh_active_effects_list()
        self.refresh_done_effects_list()

    def set_lore_block(self, block: Optional[LoreBlock]):
        self._loading = True
        try:
            self._set_lore_block_internal(block)
        finally:
            self._loading = False

    def _set_lore_block_internal(self, block: Optional[LoreBlock]):
        self.lore_block = block
        self.active_conditions_widget.set_controller(self.controller)
        self.done_conditions_widget.set_controller(self.controller)

        self.populate_parent_combo(block.id if block else None)

        if not block:
            self.id_edit.clear()
            self.title_edit.clear()
            self.desc_edit.clear()
            idx_ev = self.type_combo.findData("Event")
            if idx_ev >= 0:
                self.type_combo.setCurrentIndex(idx_ev)
            self._apply_type_styling("Event")
            self._apply_type_layout("Event")
            self.active_conditions_widget.set_conditions([])
            self.done_conditions_widget.set_conditions([])
            self.refresh_active_effects_list()
            self.refresh_done_effects_list()
            return

        type_val = getattr(block, "type", "Event") or "Event"
        idx_type = self.type_combo.findData(type_val)
        if idx_type >= 0:
            self.type_combo.setCurrentIndex(idx_type)
        else:
            self.type_combo.setCurrentIndex(self.type_combo.findData("Event"))

        self._apply_type_styling(type_val)
        self._apply_type_layout(type_val)

        self.id_edit.setText(block.id)
        self.title_edit.setText(block.title or block.name or "")
        self.desc_edit.setPlainText(block.description or "")

        # Padre HSM
        if block.parent_id:
            idx_p = self.parent_combo.findData(block.parent_id)
            if idx_p >= 0:
                self.parent_combo.setCurrentIndex(idx_p)
            else:
                self.parent_combo.addItem(f"📁 {block.parent_id} [Externo]", block.parent_id)
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
        else:
            self.parent_combo.setCurrentIndex(0)

        # active_conditions
        if not block.active_conditions:
            block.active_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        act_group = block.active_conditions[0]
        self.active_conditions_widget.set_conditions(act_group.conditions)
        self.rag_active_check.setChecked(act_group.rag_enabled)
        self.phrases_active_edit.setPlainText("\n".join(act_group.trigger_phrases))
        self.phrases_active_edit.setVisible(act_group.rag_enabled)

        # done_conditions
        if not block.done_conditions:
            block.done_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        done_group = block.done_conditions[0]
        self.done_conditions_widget.set_conditions(done_group.conditions)
        self.rag_done_check.setChecked(done_group.rag_enabled)
        self.phrases_done_edit.setPlainText("\n".join(done_group.trigger_phrases))
        self.phrases_done_edit.setVisible(done_group.rag_enabled)

        # Doble Effect
        if block.active_effects is None:
            block.active_effects = []
        if block.done_effects is None:
            block.done_effects = []
        self.refresh_active_effects_list()
        self.refresh_done_effects_list()

    def _apply_type_styling(self, type_name: str):
        meta = TYPE_METADATA.get(type_name, {"icon": "📜", "label": type_name, "color": "#5c6bc0"})
        icon = meta.get("icon", "📜")
        label = meta.get("label", type_name)
        color = meta.get("color", "#5c6bc0")
        self.header_title.setText(f"<b>{icon} {label} (HSM)</b>")
        self.header_title.setStyleSheet(f"font-size: 14px; color: {color};")

    def _apply_type_layout(self, type_name: str):
        # Todos los tipos muestran el formulario base completo
        if type_name == "popup":
            self.desc_edit.setPlaceholderText("Mensaje o contenido del aviso emergente a mostrar al jugador...")
        else:
            self.desc_edit.setPlaceholderText("Descripción interna o contexto del bloque...")

    def on_type_changed(self):
        if not self.lore_block or self._loading:
            return
        type_val = self.type_combo.currentData() or "Event"
        self.lore_block.type = type_val
        self._apply_type_styling(type_val)
        self._apply_type_layout(type_val)

        if self.parent_app and hasattr(self.parent_app, "refresh_tree"):
            self.parent_app.refresh_tree()
        self.on_field_changed()

    def on_title_changed(self, text: str):
        if not self.lore_block or self._loading:
            return
        self.lore_block.title = text
        self.lore_block.name = text
        if self.parent_app and hasattr(self.parent_app, "update_selected_tree_item_text"):
            self.parent_app.update_selected_tree_item_text(text)

    def on_parent_changed(self):
        if not self.lore_block or self._loading:
            return
        p_val = self.parent_combo.currentData()
        self.lore_block.parent_id = str(p_val).strip() if p_val and str(p_val).strip() else None
        if self.parent_app and hasattr(self.parent_app, "refresh_tree"):
            self.parent_app.refresh_tree()

    def on_add_any_condition(self):
        if self.type_combo.currentData() == "popup":
            self.active_conditions_widget.on_add_condition()
            return
        menu = QMenu(self)
        act_active = menu.addAction("🟢 Requisito Previo (active_conditions)...")
        act_done = menu.addAction("🔵 Condición de Salida (done_conditions)...")
        pos = self.add_cond_btn.mapToGlobal(QPoint(0, self.add_cond_btn.height()))
        chosen = menu.exec(pos)
        if chosen == act_active:
            self.active_conditions_widget.on_add_condition()
        elif chosen == act_done:
            self.done_conditions_widget.on_add_condition()

    def on_active_conditions_changed(self):
        if not self.lore_block or self._loading:
            return
        if not self.lore_block.active_conditions:
            self.lore_block.active_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        self.lore_block.active_conditions[0].conditions = self.active_conditions_widget.get_conditions()
        self.on_field_changed()

    def on_done_conditions_changed(self):
        if not self.lore_block or self._loading:
            return
        if not self.lore_block.done_conditions:
            self.lore_block.done_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        self.lore_block.done_conditions[0].conditions = self.done_conditions_widget.get_conditions()
        self.on_field_changed()

    def on_rag_active_toggled(self, checked: bool):
        self.phrases_active_edit.setVisible(checked)
        if self._loading:
            return
        if self.lore_block and self.lore_block.active_conditions:
            self.lore_block.active_conditions[0].rag_enabled = checked
        self.on_field_changed()

    def on_rag_done_toggled(self, checked: bool):
        self.phrases_done_edit.setVisible(checked)
        if self._loading:
            return
        if self.lore_block and self.lore_block.done_conditions:
            self.lore_block.done_conditions[0].rag_enabled = checked
        self.on_field_changed()

    def on_field_changed(self):
        if not self.lore_block or self._loading:
            return

        self.lore_block.id = self.id_edit.text().strip()
        self.lore_block.type = self.type_combo.currentData() or "Event"
        self.lore_block.description = self.desc_edit.toPlainText().strip()

        if self.lore_block.active_conditions:
            phrases = [p.strip() for p in self.phrases_active_edit.toPlainText().split("\n") if p.strip()]
            self.lore_block.active_conditions[0].trigger_phrases = phrases

        if self.lore_block.done_conditions:
            done_phrases = [p.strip() for p in self.phrases_done_edit.toPlainText().split("\n") if p.strip()]
            self.lore_block.done_conditions[0].trigger_phrases = done_phrases

        self.lore_changed.emit()

    def on_delete_clicked(self):
        if self.lore_block and self.parent_app and hasattr(self.parent_app, "delete_lore_block"):
            self.parent_app.delete_lore_block(self.lore_block)

    def refresh_active_effects_list(self):
        while self.active_effects_container_layout.count():
            item = self.active_effects_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.lore_block or not self.lore_block.active_effects:
            empty_lbl = QLabel(
                "Sin efectos al activar (active_effects).\nHaz clic en '➕ Añadir Efecto al Activar...' para configurar uno.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #888; font-style: italic; padding: 10px; font-size: 11px;")
            self.active_effects_container_layout.addWidget(empty_lbl)
            return

        for idx, eff in enumerate(self.lore_block.active_effects):
            card = self._create_effect_card(idx, eff, is_active=True)
            self.active_effects_container_layout.addWidget(card)

    def refresh_done_effects_list(self):
        while self.done_effects_container_layout.count():
            item = self.done_effects_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.lore_block or not self.lore_block.done_effects:
            empty_lbl = QLabel(
                "Sin efectos al completar (done_effects).\nHaz clic en '➕ Añadir Efecto al Completar...' para configurar uno.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #888; font-style: italic; padding: 10px; font-size: 11px;")
            self.done_effects_container_layout.addWidget(empty_lbl)
            return

        for idx, eff in enumerate(self.lore_block.done_effects):
            card = self._create_effect_card(idx, eff, is_active=False)
            self.done_effects_container_layout.addWidget(card)

    def _create_effect_card(self, index: int, eff: LoreEffects, is_active: bool = True) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #cfcfcf;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QFrame:hover {
                background: #f0f7ff;
                border-color: #3399ff;
            }
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # 1. Badge de Acción (Hook vs Push)
        action_badge = QLabel()
        action_badge.setStyleSheet("padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold;")
        if eff.action == "push":
            action_badge.setText("⚡ Push")
            action_badge.setStyleSheet(
                action_badge.styleSheet() + "background: #fff3e0; color: #e65100; border: 1px solid #ffe0b2;")
            action_badge.setToolTip("Acción forzada inmediata del loreblock")
        else:
            action_badge.setText("🎧 Hook")
            action_badge.setStyleSheet(
                action_badge.styleSheet() + "background: #ede7f6; color: #512da8; border: 1px solid #d1c4e9;")
            action_badge.setToolTip("Acción pasiva al interactuar con la entidad")
        layout.addWidget(action_badge)

        # 2. Entidad Objetivo
        target_badge = QLabel()
        target_badge.setStyleSheet(
            "padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold; background: #f5f5f5; color: #333; border: 1px solid #e0e0e0;")
        badge_text = self._resolve_entity_badge(eff.target)
        target_badge.setText(badge_text)
        layout.addWidget(target_badge)

        # 3. Directiva compacta
        dir_text = (eff.directive or "").strip()
        if dir_text:
            dir_snip = dir_text[:50] + "..." if len(dir_text) > 50 else dir_text
            dir_lbl = QLabel(f"<i>&ldquo;{dir_snip}&rdquo;</i>")
            dir_lbl.setStyleSheet("color: #444; font-size: 11px;")
        else:
            dir_lbl = QLabel("<i>(Sin directiva)</i>")
            dir_lbl.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(dir_lbl, 1)

        # 4. Badge de Tiempo Transcurrido (si > 00:00)
        if eff.elapsed_time and eff.elapsed_time != "00:00":
            time_badge = QLabel(f"⏳ {eff.elapsed_time}")
            time_badge.setStyleSheet(
                "padding: 2px 5px; border-radius: 3px; font-size: 10px; font-weight: bold; background: #e0f2f1; color: #00695c; border: 1px solid #b2dfdb;")
            time_badge.setToolTip("Tiempo de juego sumado")
            layout.addWidget(time_badge)

        # 5. Mutaciones
        mut_tags = self._format_card_mutations(eff)
        if mut_tags:
            mut_lbl = QLabel("  ".join(mut_tags))
            mut_lbl.setStyleSheet("color: #0d47a1; font-size: 10px;")
            layout.addWidget(mut_lbl)

        # Botones de edición y borrado
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Editar efecto (o doble clic)")
        edit_btn.setStyleSheet("border: none; background: transparent; padding: 2px 4px; font-size: 12px;")
        if is_active:
            edit_btn.clicked.connect(lambda _, i=index: self.on_edit_active_effect_clicked(i))
        else:
            edit_btn.clicked.connect(lambda _, i=index: self.on_edit_done_effect_clicked(i))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setToolTip("Eliminar efecto")
        del_btn.setStyleSheet(
            "border: none; background: transparent; color: #cc0000; font-weight: bold; padding: 2px 4px; font-size: 12px;")
        if is_active:
            del_btn.clicked.connect(lambda _, i=index: self.on_delete_active_effect_clicked(i))
        else:
            del_btn.clicked.connect(lambda _, i=index: self.on_delete_done_effect_clicked(i))
        layout.addWidget(del_btn)

        if is_active:
            card.mouseDoubleClickEvent = lambda event, i=index: self.on_edit_active_effect_clicked(i)
        else:
            card.mouseDoubleClickEvent = lambda event, i=index: self.on_edit_done_effect_clicked(i)
        return card

    def _resolve_entity_badge(self, target_id: Optional[str]) -> str:
        if not target_id or not str(target_id).strip():
            return "🌐 Global"

        tid = str(target_id).strip()
        if self.controller:
            etype, name, emoji = self.controller.resolve_entity_info(tid)
            if etype != "unknown":
                return f"{emoji} {name}"

        return f"🔹 {tid}"

    def _format_card_mutations(self, eff: LoreEffects) -> List[str]:
        tags = []
        if eff.gold_delta != 0:
            tags.append(f"💰 {eff.gold_delta:+d} Oro")
        if eff.affinity_delta != 0.0:
            tags.append(f"❤️ {eff.affinity_delta:+.2f}")
        for it in eff.give_items:
            tags.append(f"🎁 +{it}")
        for it in eff.take_items:
            tags.append(f"📤 -{it}")
        for p in eff.unlock_places:
            tags.append(f"📍 Revelar {p}")
        for n in eff.unlock_npcs:
            tags.append(f"👤 Revelar {n}")
        for i in eff.unlock_items:
            tags.append(f"📦 Revelar {i}")
        for bp in eff.block_places:
            tags.append(f"🚫 {bp}")
        for up in eff.unblock_places:
            tags.append(f"🔓 {up}")
        if eff.bypass_llm:
            tags.append("⚡ Bypass LLM")
        return tags

    def on_add_active_effect_clicked(self):
        if not self.lore_block:
            return
        is_pop = bool(getattr(self.lore_block, "type", "") == "popup")
        dialog = LoreEffectDialog(controller=self.controller, parent=self, is_popup=is_pop)
        dialog.setWindowTitle("Configurar Efecto al Activar (active_effects)")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_eff = dialog.get_effect()
            if self.lore_block.active_effects is None:
                self.lore_block.active_effects = []
            self.lore_block.active_effects.append(new_eff)
            self.refresh_active_effects_list()
            self.lore_changed.emit()

    def on_edit_active_effect_clicked(self, index: int):
        if not self.lore_block or not self.lore_block.active_effects or index < 0 or index >= len(
                self.lore_block.active_effects):
            return
        is_pop = bool(getattr(self.lore_block, "type", "") == "popup")
        dialog = LoreEffectDialog(
            effect=self.lore_block.active_effects[index],
            controller=self.controller,
            parent=self,
            is_popup=is_pop,
        )
        dialog.setWindowTitle("Configurar Efecto al Activar (active_effects)")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.lore_block.active_effects[index] = dialog.get_effect()
            self.refresh_active_effects_list()
            self.lore_changed.emit()

    def on_delete_active_effect_clicked(self, index: int):
        if not self.lore_block or not self.lore_block.active_effects or index < 0 or index >= len(
                self.lore_block.active_effects):
            return
        self.lore_block.active_effects.pop(index)
        self.refresh_active_effects_list()
        self.lore_changed.emit()

    def on_add_done_effect_clicked(self):
        if not self.lore_block:
            return
        is_pop = bool(getattr(self.lore_block, "type", "") == "popup")
        dialog = LoreEffectDialog(controller=self.controller, parent=self, is_popup=is_pop)
        dialog.setWindowTitle("Configurar Efecto al Completar (done_effects)")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_eff = dialog.get_effect()
            if self.lore_block.done_effects is None:
                self.lore_block.done_effects = []
            self.lore_block.done_effects.append(new_eff)
            self.refresh_done_effects_list()
            self.lore_changed.emit()

    def on_edit_done_effect_clicked(self, index: int):
        if not self.lore_block or not self.lore_block.done_effects or index < 0 or index >= len(
                self.lore_block.done_effects):
            return
        is_pop = bool(getattr(self.lore_block, "type", "") == "popup")
        dialog = LoreEffectDialog(
            effect=self.lore_block.done_effects[index],
            controller=self.controller,
            parent=self,
            is_popup=is_pop,
        )
        dialog.setWindowTitle("Configurar Efecto al Completar (done_effects)")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.lore_block.done_effects[index] = dialog.get_effect()
            self.refresh_done_effects_list()
            self.lore_changed.emit()

    def on_delete_done_effect_clicked(self, index: int):
        if not self.lore_block or not self.lore_block.done_effects or index < 0 or index >= len(
                self.lore_block.done_effects):
            return
        self.lore_block.done_effects.pop(index)
        self.refresh_done_effects_list()
        self.lore_changed.emit()

    def populate_parent_combo(self, current_id: Optional[str]):
        self.parent_combo.blockSignals(True)
        self.parent_combo.clear()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")

        if not self.controller:
            self.parent_combo.blockSignals(False)
            return

        all_blocks = self.controller.get_lore_blocks()

        forbidden = set()
        if current_id:
            forbidden.add(current_id)
            changed = True
            while changed:
                changed = False
                for b in all_blocks:
                    if b.id not in forbidden and getattr(b, "parent_id", None) in forbidden:
                        forbidden.add(b.id)
                        changed = True

        for b in all_blocks:
            if b.id in forbidden:
                continue
            title = b.title or b.name or b.id
            self.parent_combo.addItem(f"📁 {title} ({b.id})", b.id)

        self.parent_combo.blockSignals(False)
