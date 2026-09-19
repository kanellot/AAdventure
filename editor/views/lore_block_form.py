"""Formulario central para la edición completa de un Bloque de Lore (HSM):
1. Pestaña General: ID, Título, Descripción, Bloque Padre HSM (📁).
2. Pestaña Condiciones Active: Condiciones de estado previas y Antenas RAG de activación.
3. Pestaña Condiciones Done: Condiciones de estado de salida y Antenas RAG de finalización.
4. Pestaña Efectos: Dos sub-pestañas independientes (On Active y On Done) con selección de objetivo (target), directiva LLM, acción forzada y mutaciones.
"""

from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTabWidget, QMessageBox, QPushButton, QScrollArea, QFrame,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from domains.lore import LoreBlock, LoreEffects
from editor.views.compact_widgets import CompactConditionListWidget, CompactEntityListWidget
from editor.views.entity_picker import EntityPickerDialog


class LoreEffectDialog(QDialog):
    """Diálogo modal para crear o editar un efecto individual sobre una entidad (active o done)."""

    def __init__(self, effect: Optional[LoreEffects] = None, controller=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Efecto de Lore")
        self.resize(560, 680)
        self.controller = controller
        self.effect: LoreEffects = effect.model_copy(deep=True) if effect else LoreEffects(timing="active")

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

        # 1. Momento de Disparo (Timing)
        timing_group = QGroupBox("Momento de Activación del Efecto")
        timing_form = QFormLayout(timing_group)
        self.timing_combo = QComboBox()
        self.timing_combo.addItem("🟢 Al pasar a Active (on_active)", "active")
        self.timing_combo.addItem("🔵 Al pasar a Done (on_done)", "done")
        timing_form.addRow("Disparar efecto:", self.timing_combo)
        layout.addWidget(timing_group)

        # 2. Objetivo / Target
        target_group = QGroupBox("Entidad Objetivo (Target)")
        target_form = QFormLayout(target_group)

        target_row = QHBoxLayout()
        self.target_combo = QComboBox()
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)
        target_row.addWidget(self.target_combo, 1)

        self.pick_btn = QPushButton("🔍 Seleccionar...")
        self.pick_btn.setToolTip("Abrir diálogo de selección de entidades (Lugares, NPCs, Objetos, LoreBlocks)")
        self.pick_btn.setStyleSheet("padding: 3px 8px; font-weight: bold;")
        self.pick_btn.clicked.connect(self.on_pick_target)
        target_row.addWidget(self.pick_btn)

        target_form.addRow("Entidad Objetivo:", target_row)

        target_hint = QLabel(
            "<i>Selecciona la entidad a la que afectará este efecto. Si eliges '(Ninguno)', "
            "el LoreBlock actuará como estado puro o efecto global sin vincularse a una entidad particular.</i>"
        )
        target_hint.setStyleSheet("color: #666; font-size: 11px;")
        target_hint.setWordWrap(True)
        target_form.addRow(target_hint)
        layout.addWidget(target_group)

        # 3. Directiva y Bypass de LLM
        dir_group = QGroupBox("Directiva / Mensaje Narrativo")
        dir_vbox = QVBoxLayout(dir_group)
        self.directive_edit = QTextEdit()
        self.directive_edit.setPlaceholderText("Instrucción narrativa inyectada o texto exacto para el jugador...")
        self.directive_edit.setMaximumHeight(80)
        dir_vbox.addWidget(self.directive_edit)

        self.bypass_llm_check = QCheckBox("⚡ Bypasear LLM (Respuesta directa exacta sin llamar a IA)")
        self.bypass_llm_check.setToolTip(
            "Si está marcado, la directiva se entrega textualmente al jugador como réplica de diálogo "
            "o descripción de inspección sin consultar al LLM ni consumir tokens."
        )
        dir_vbox.addWidget(self.bypass_llm_check)
        layout.addWidget(dir_group)

        # 4. Modo de Ejecución (Push vs Hook) y Acción Automatizada
        auto_group = QGroupBox("Modo de Ejecución y Acción Automatizada")
        auto_vbox = QVBoxLayout(auto_group)

        exec_form = QFormLayout()
        self.exec_mode_combo = QComboBox()
        self.exec_mode_combo.addItem("⚡ Push (Inmediato / Acción automática del sistema)", "push")
        self.exec_mode_combo.addItem("🎧 Hook (Reactivo / En espera de interacción del jugador)", "hook")
        self.exec_mode_combo.currentIndexChanged.connect(self.on_exec_mode_changed)
        exec_form.addRow("Comportamiento:", self.exec_mode_combo)
        auto_vbox.addLayout(exec_form)

        self.force_check = QCheckBox("Forzar acción automática del sistema")
        self.force_check.toggled.connect(self.on_force_toggled)
        auto_vbox.addWidget(self.force_check)

        self.auto_panel = QWidget()
        auto_form = QFormLayout(self.auto_panel)
        auto_form.setContentsMargins(0, 4, 0, 0)

        self.auto_type_combo = QComboBox()
        self.auto_type_combo.addItem("💬 Iniciar Diálogo (TALK)", "TALK")
        self.auto_type_combo.addItem("👁️ Describir / Inspeccionar (EXPLAIN)", "EXPLAIN")
        self.auto_type_combo.currentIndexChanged.connect(self.on_auto_type_changed)
        auto_form.addRow("Tipo de Acción:", self.auto_type_combo)

        auto_target_row = QHBoxLayout()
        self.auto_target_combo = QComboBox()
        auto_target_row.addWidget(self.auto_target_combo, 1)

        self.auto_pick_btn = QPushButton("🔍 Seleccionar...")
        self.auto_pick_btn.setToolTip("Abrir diálogo de selección de entidades para la acción automática")
        self.auto_pick_btn.setStyleSheet("padding: 3px 8px;")
        self.auto_pick_btn.clicked.connect(self.on_pick_auto_target)
        auto_target_row.addWidget(self.auto_pick_btn)

        auto_form.addRow("Objetivo de la Acción:", auto_target_row)

        auto_vbox.addWidget(self.auto_panel)
        self.auto_panel.setVisible(False)
        layout.addWidget(auto_group)

        # 5. Mutaciones al Gamestate
        eff_group = QGroupBox("Mutaciones sobre el Estado del Juego")
        eff_form = QFormLayout(eff_group)

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
        eff_form.addRow(row_deltas)
        layout.addWidget(eff_group)

        # 6. Objetos Modificados en el Inventario
        items_group = QGroupBox("Objetos Modificados en el Inventario")
        items_layout = QHBoxLayout(items_group)

        give_vbox = QVBoxLayout()
        give_vbox.addWidget(QLabel("<b>Entregar al Jugador:</b>"))
        self.give_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Entregar Objeto...", parent=items_group
        )
        give_vbox.addWidget(self.give_items_widget)
        items_layout.addLayout(give_vbox)

        take_vbox = QVBoxLayout()
        take_vbox.addWidget(QLabel("<b>Retirar del Jugador:</b>"))
        self.take_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Retirar Objeto...", parent=items_group
        )
        take_vbox.addWidget(self.take_items_widget)
        items_layout.addLayout(take_vbox)

        layout.addWidget(items_group)

        # 7. Conexiones
        conns_group = QGroupBox("Control de Paso de Conexiones (Bidireccional)")
        conns_layout = QHBoxLayout(conns_group)

        block_vbox = QVBoxLayout()
        block_vbox.addWidget(QLabel("<b>🚫 Bloquear Paso hacia:</b>"))
        self.block_conns_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["place"], button_text="➕ Bloquear Conexión...", parent=conns_group
        )
        block_vbox.addWidget(self.block_conns_widget)
        conns_layout.addLayout(block_vbox)

        allow_vbox = QVBoxLayout()
        allow_vbox.addWidget(QLabel("<b>🟢 Permitir / Abrir Paso hacia:</b>"))
        self.allow_conns_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["place"], button_text="➕ Abrir Conexión...", parent=conns_group
        )
        allow_vbox.addWidget(self.allow_conns_widget)
        conns_layout.addLayout(allow_vbox)

        layout.addWidget(conns_group)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Botones inferiores OK / Cancelar
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("Guardar Efecto")
        btn_box.button(QDialogButtonBox.Cancel).setText("Cancelar")
        btn_box.accepted.connect(self.on_accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        # Cargar datos iniciales
        self.populate_target_combo(self.effect.target)
        self.load_data(self.effect)

    def populate_target_combo(self, current_value: Optional[str] = None):
        """Rellena el selector de objetivo con todas las entidades disponibles."""
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("(Ninguno - Efecto Global / Sin Objetivo)", "")

        if self.controller:
            npcs = getattr(self.controller, "get_all_npcs", lambda: [])() or getattr(self.controller, "get_npcs", lambda: [])()
            for n in npcs:
                self.target_combo.addItem(f"👤 {n.name} ({n.id})", n.id)

            places = getattr(self.controller, "get_all_places", lambda: [])()
            for p in places:
                self.target_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

            objs = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
            for o in objs:
                self.target_combo.addItem(f"📦 {o.name} ({o.id})", o.id)

        if current_value:
            idx = self.target_combo.findData(current_value)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
            else:
                for i in range(self.target_combo.count()):
                    if current_value.lower() in self.target_combo.itemText(i).lower():
                        self.target_combo.setCurrentIndex(i)
                        break
                else:
                    self.target_combo.addItem(f"🔹 {current_value} (Personalizado)", current_value)
                    self.target_combo.setCurrentIndex(self.target_combo.count() - 1)
        else:
            self.target_combo.setCurrentIndex(0)

        self.target_combo.blockSignals(False)

    def load_data(self, eff: LoreEffects):
        idx_t = self.timing_combo.findData(eff.timing)
        if idx_t >= 0:
            self.timing_combo.setCurrentIndex(idx_t)

        self.directive_edit.setPlainText(eff.directive or "")
        self.bypass_llm_check.setChecked(getattr(eff, "bypass_llm", False))

        exec_mode = getattr(eff, "execution_mode", "push")
        idx_exec = self.exec_mode_combo.findData(exec_mode)
        if idx_exec >= 0:
            self.exec_mode_combo.setCurrentIndex(idx_exec)
        self.on_exec_mode_changed()

        delta = eff.gold_delta if eff.gold_delta != 0 else (eff.give_gold - eff.take_gold)
        self.gold_spin.setValue(delta)
        self.affinity_spin.setValue(eff.affinity_delta)

        self.give_items_widget.set_entity_ids(eff.give_items or [])
        self.take_items_widget.set_entity_ids(eff.take_items or [])
        self.block_conns_widget.set_entity_ids(eff.block_connections or [])
        self.allow_conns_widget.set_entity_ids(eff.allow_connections or [])

        is_forced = bool(eff.force_action or eff.trigger_action_type)
        self.force_check.setChecked(is_forced)
        self.auto_panel.setVisible(is_forced)

        if eff.trigger_action_type:
            idx_act = self.auto_type_combo.findData(eff.trigger_action_type.upper())
            if idx_act >= 0:
                self.auto_type_combo.setCurrentIndex(idx_act)

        self._update_auto_target_options(current_selection=eff.trigger_action_target or eff.target)

    def on_exec_mode_changed(self):
        mode = self.exec_mode_combo.currentData()
        if mode == "hook":
            self.force_check.setChecked(False)
            self.force_check.setEnabled(False)
        else:
            self.force_check.setEnabled(True)

    def on_target_changed(self):
        selected_target = self.target_combo.currentData()
        if self.force_check.isChecked() and selected_target:
            self._auto_detect_action_type(selected_target)
        else:
            self._update_auto_target_options(current_selection=selected_target)

    def on_force_toggled(self, checked: bool):
        self.auto_panel.setVisible(checked)
        if checked:
            selected_target = self.target_combo.currentData()
            if selected_target:
                self._auto_detect_action_type(selected_target)
            else:
                self._update_auto_target_options()

    def on_auto_type_changed(self):
        selected_target = self.target_combo.currentData()
        self._update_auto_target_options(current_selection=selected_target)

    def on_pick_target(self):
        current_target = self.target_combo.currentData() or ""
        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=["place", "npc", "item", "loreblock"],
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

    def on_pick_auto_target(self):
        act_type = self.auto_type_combo.currentData() or "TALK"
        allowed = ["npc"] if act_type == "TALK" else ["place"]
        current_target = self.auto_target_combo.currentData() or ""

        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=allowed,
            mode="entity_only",
            initial_entity_id=current_target,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = dialog.get_selected_entity_id()
            if selected_id:
                idx = self.auto_target_combo.findData(selected_id)
                if idx >= 0:
                    self.auto_target_combo.setCurrentIndex(idx)
                else:
                    selected_name = dialog.get_selected_entity_name() or selected_id
                    emoji = "👤 " if act_type == "TALK" else "📍 "
                    self.auto_target_combo.addItem(f"{emoji}{selected_name} ({selected_id})", selected_id)
                    self.auto_target_combo.setCurrentIndex(self.auto_target_combo.count() - 1)

    def _auto_detect_action_type(self, target_id: str):
        is_npc = False
        is_place = False
        if self.controller and hasattr(self.controller, "world_state"):
            if target_id in self.controller.world_state.npcs or target_id in getattr(self.controller.world_state, "npcs_by_name", {}):
                is_npc = True
            elif target_id in self.controller.world_state.places_by_id or target_id in getattr(self.controller.world_state, "places_by_name", {}):
                is_place = True

        if is_npc:
            idx = self.auto_type_combo.findData("TALK")
            if idx >= 0:
                self.auto_type_combo.setCurrentIndex(idx)
        elif is_place:
            idx = self.auto_type_combo.findData("EXPLAIN")
            if idx >= 0:
                self.auto_type_combo.setCurrentIndex(idx)

        self._update_auto_target_options(current_selection=target_id)

    def _update_auto_target_options(self, current_selection: Optional[str] = None):
        self.auto_target_combo.blockSignals(True)
        self.auto_target_combo.clear()

        act_type = self.auto_type_combo.currentData() or "TALK"
        main_target = self.target_combo.currentData()

        if main_target:
            prefix_emoji = "👤 " if act_type == "TALK" else "📍 "
            self.auto_target_combo.addItem(f"{prefix_emoji}{main_target}", main_target)

        if self.controller:
            if act_type == "TALK":
                for n in getattr(self.controller, "get_all_npcs", lambda: [])() or getattr(self.controller, "get_npcs", lambda: [])():
                    if n.id != main_target and n.name != main_target:
                        self.auto_target_combo.addItem(f"👤 {n.name} ({n.id})", n.id)
            else:
                for p in getattr(self.controller, "get_all_places", lambda: [])():
                    if p.id != main_target and p.name != main_target:
                        self.auto_target_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

        if current_selection:
            idx = self.auto_target_combo.findData(current_selection)
            if idx >= 0:
                self.auto_target_combo.setCurrentIndex(idx)
            else:
                prefix_emoji = "👤 " if act_type == "TALK" else "📍 "
                self.auto_target_combo.addItem(f"{prefix_emoji}{current_selection}", current_selection)
                self.auto_target_combo.setCurrentIndex(self.auto_target_combo.count() - 1)

        self.auto_target_combo.blockSignals(False)

    def _update_effect_from_ui(self):
        self.effect.timing = self.timing_combo.currentData() or "active"
        self.effect.target = self.target_combo.currentData() or None
        self.effect.directive = self.directive_edit.toPlainText().strip()
        self.effect.bypass_llm = self.bypass_llm_check.isChecked()
        self.effect.execution_mode = self.exec_mode_combo.currentData() or "push"

        gold_val = self.gold_spin.value()
        self.effect.gold_delta = gold_val
        self.effect.give_gold = gold_val if gold_val > 0 else 0
        self.effect.take_gold = abs(gold_val) if gold_val < 0 else 0
        self.effect.affinity_delta = self.affinity_spin.value()

        self.effect.give_items = self.give_items_widget.get_entity_ids()
        self.effect.take_items = self.take_items_widget.get_entity_ids()
        self.effect.block_connections = self.block_conns_widget.get_entity_ids()
        self.effect.allow_connections = self.allow_conns_widget.get_entity_ids()

        self.effect.force_action = self.force_check.isChecked()
        if self.effect.force_action:
            self.effect.trigger_action_type = self.auto_type_combo.currentData()
            self.effect.trigger_action_target = self.auto_target_combo.currentData()
        else:
            self.effect.trigger_action_type = None
            self.effect.trigger_action_target = None

    def on_accept(self):
        self._update_effect_from_ui()
        self.accept()

    def get_effect(self) -> LoreEffects:
        self._update_effect_from_ui()
        return self.effect


class LoreBlockForm(QWidget):
    """Formulario integral para la configuración de un LoreBlock (HSM)."""

    lore_changed = Signal()

    @staticmethod
    def _create_scroll_tab(widget: QWidget) -> QScrollArea:
        """Envuelve un widget de pestaña en un área de desplazamiento suave sin bordes feos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setWidget(widget)
        return scroll

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.parent_app = parent
        self.lore_block: Optional[LoreBlock] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con botón de eliminar
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

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # =====================================================================
        # PESTAÑA 1: General (Sin selección manual de estado ni target global)
        # =====================================================================
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)

        props_group = QGroupBox("Propiedades Generales del LoreBlock")
        props_form = QFormLayout(props_group)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("📖 Capítulo (Contenedor Principal)", "chapter")
        self.preset_combo.addItem("⚔️ Quest (Misión Principal)", "quest")
        self.preset_combo.addItem("📌 Tarea / Task (Objetivo Concreto)", "task")
        self.preset_combo.addItem("💬 Evento Diálogo (Interacción con NPC)", "event_diag")
        self.preset_combo.addItem("👁️ Evento Inspección (Examinar Lugar/Objeto)", "event_look")
        self.preset_combo.addItem("📢 Evento Pop-up (Aviso Directo)", "event_popup")
        self.preset_combo.addItem("⚡ Evento Libre / Personalizado", "event")
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        props_form.addRow("Tipo de Bloque (Preset):", self.preset_combo)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("pista_mago_taberna")
        self.id_edit.textChanged.connect(self.on_field_changed)
        props_form.addRow("ID Único:", self.id_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título descriptivo del secreto o misión...")
        self.title_edit.textChanged.connect(self.on_title_changed)
        props_form.addRow("Título:", self.title_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Notas internas del diseñador o contexto del bloque...")
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.textChanged.connect(self.on_field_changed)
        props_form.addRow("Descripción:", self.desc_edit)

        self.parent_combo = QComboBox()
        self.parent_combo.currentIndexChanged.connect(self.on_parent_changed)
        props_form.addRow("Carpeta / Bloque Padre (HSM):", self.parent_combo)

        gen_layout.addWidget(props_group)

        # Nota informativa sobre el ciclo de vida automático
        info_note = QLabel(
            "ℹ️ <b>Ciclo de Vida Automático (HSM)</b>:<br>"
            "• Si no defines condiciones para Active, el bloque se activará al iniciar la aventura.<br>"
            "• Si no defines condiciones para Done, el bloque pasará a Done inmediatamente al activarse.<br>"
            "• Los bloques hijos solo se evaluarán cuando todos sus padres estén en estado Active.<br>"
            "• Los objetivos (targets) y directivas se configuran de forma independiente en la pestaña <b>Efectos</b>."
        )
        info_note.setStyleSheet("background: #f0f4f8; border: 1px solid #d0dbe5; border-radius: 4px; padding: 8px; color: #334e68; font-size: 11px;")
        info_note.setWordWrap(True)
        gen_layout.addWidget(info_note)
        gen_layout.addStretch()

        self.tab_widget.addTab(self._create_scroll_tab(self.tab_general), "General")

        # =====================================================================
        # PESTAÑA 2: Condiciones Active
        # =====================================================================
        self.tab_active = QWidget()
        active_layout = QVBoxLayout(self.tab_active)

        cond_group = QGroupBox("1. Condiciones de Estado (Requisito Previo Obligatorio)")
        cond_vbox = QVBoxLayout(cond_group)
        cond_desc = QLabel(
            "El bloque pasará a Active cuando se cumplan TODAS estas condiciones conjuntamente (AND). "
            "Si está vacía, se activará automáticamente si sus padres están activos."
        )
        cond_desc.setStyleSheet("color: #444; font-size: 11px;")
        cond_desc.setWordWrap(True)
        cond_vbox.addWidget(cond_desc)

        self.active_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=cond_group)
        self.active_conditions_widget.conditions_changed.connect(self.on_active_conditions_changed)
        cond_vbox.addWidget(self.active_conditions_widget)
        active_layout.addWidget(cond_group)

        rag_group = QGroupBox("2. Antenas Semánticas RAG de Activación (Opcional)")
        rag_vbox = QVBoxLayout(rag_group)

        self.rag_active_check = QCheckBox("Habilitar antenas semánticas (vigilar entrada del jugador solo si se cumplen condiciones)")
        self.rag_active_check.toggled.connect(self.on_rag_active_toggled)
        rag_vbox.addWidget(self.rag_active_check)

        self.phrases_edit = QTextEdit()
        self.phrases_edit.setPlaceholderText("Introduce una frase gatillo por línea (ej: ¿Has visto al nigromante?)...")
        self.phrases_edit.setMaximumHeight(80)
        self.phrases_edit.textChanged.connect(self.on_field_changed)
        rag_vbox.addWidget(self.phrases_edit)

        rag_note = QLabel("<i>Si las antenas están desactivadas o vacías, el bloque se activará automáticamente al cumplir condiciones.</i>")
        rag_note.setStyleSheet("color: #666; font-size: 11px;")
        rag_vbox.addWidget(rag_note)
        active_layout.addWidget(rag_group)
        active_layout.addStretch()

        self.tab_widget.addTab(self._create_scroll_tab(self.tab_active), "Condiciones Active")

        # =====================================================================
        # PESTAÑA 3: Condiciones Done (Sin checkbox de repetición)
        # =====================================================================
        self.tab_done = QWidget()
        done_layout = QVBoxLayout(self.tab_done)

        exit_group = QGroupBox("1. Condiciones de Salida (Para pasar a Done)")
        exit_vbox = QVBoxLayout(exit_group)
        exit_desc = QLabel(
            "Condiciones de estado necesarias para dar por finalizado el bloque y pasar a Done. "
            "Si no se define ninguna condición de salida, el bloque concluirá pasando a Done inmediatamente tras activarse."
        )
        exit_desc.setStyleSheet("color: #444; font-size: 11px;")
        exit_desc.setWordWrap(True)
        exit_vbox.addWidget(exit_desc)

        self.exit_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=exit_group)
        self.exit_conditions_widget.conditions_changed.connect(self.on_exit_conditions_changed)
        exit_vbox.addWidget(self.exit_conditions_widget)
        done_layout.addWidget(exit_group)

        rag_exit_group = QGroupBox("2. Antenas Semánticas RAG de Finalización (Opcional)")
        rag_exit_vbox = QVBoxLayout(rag_exit_group)

        self.rag_exit_check = QCheckBox("Habilitar antenas semánticas de salida (vigilar solo si se cumplen las condiciones)")
        self.rag_exit_check.toggled.connect(self.on_rag_exit_toggled)
        rag_exit_vbox.addWidget(self.rag_exit_check)

        self.exit_phrases_edit = QTextEdit()
        self.exit_phrases_edit.setPlaceholderText("Frases de conclusión por línea (ej: Acepto la recompensa, Misión cumplida)...")
        self.exit_phrases_edit.setMaximumHeight(80)
        self.exit_phrases_edit.textChanged.connect(self.on_field_changed)
        rag_exit_vbox.addWidget(self.exit_phrases_edit)

        exit_note = QLabel("<i>Si están desactivadas, pasará a Done automáticamente al cumplirse las condiciones de salida.</i>")
        exit_note.setStyleSheet("color: #666; font-size: 11px;")
        rag_exit_vbox.addWidget(exit_note)
        done_layout.addWidget(rag_exit_group)
        done_layout.addStretch()

        self.tab_widget.addTab(self._create_scroll_tab(self.tab_done), "Condiciones Done")

        # =====================================================================
        # PESTAÑA 4: Efectos (Lista de Efectos por Entidad)
        # =====================================================================
        self.tab_effects = QWidget()
        eff_layout = QVBoxLayout(self.tab_effects)
        eff_layout.setContentsMargins(8, 8, 8, 8)
        eff_layout.setSpacing(6)

        # Barra superior de la lista de efectos
        eff_top_bar = QHBoxLayout()
        eff_title = QLabel("<b>⚡ Efectos sobre Entidades (HSM)</b>")
        eff_title.setStyleSheet("font-size: 12px; color: #334e68;")
        eff_top_bar.addWidget(eff_title)
        eff_top_bar.addStretch()

        self.add_effect_btn = QPushButton("➕ Añadir Efecto...")
        self.add_effect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.add_effect_btn.clicked.connect(self.on_add_effect_clicked)
        eff_top_bar.addWidget(self.add_effect_btn)
        eff_layout.addLayout(eff_top_bar)

        eff_desc = QLabel(
            "Define efectos independientes para diferentes entidades asociadas a este LoreBlock. "
            "Cada entrada especifica si se aplica al pasar a <b>Active</b> o a <b>Done</b>.<br>"
            "💡 <i>Haz doble clic sobre cualquier fila o pulsa '✏️ Editar' para modificar sus propiedades.</i>"
        )
        eff_desc.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 4px;")
        eff_desc.setWordWrap(True)
        eff_layout.addWidget(eff_desc)

        # Contenedor desplazable de fichas de efectos
        self.effects_scroll = QScrollArea()
        self.effects_scroll.setWidgetResizable(True)
        self.effects_scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")

        self.effects_container = QWidget()
        self.effects_container_layout = QVBoxLayout(self.effects_container)
        self.effects_container_layout.setContentsMargins(6, 6, 6, 6)
        self.effects_container_layout.setSpacing(6)
        self.effects_container_layout.setAlignment(Qt.AlignTop)

        self.effects_scroll.setWidget(self.effects_container)
        eff_layout.addWidget(self.effects_scroll)

        self.tab_widget.addTab(self.tab_effects, "Efectos")

        # Elementos de retrocompatibilidad para pruebas y componentes externos
        self.active_pick_btn = QPushButton("🔍 Seleccionar...")
        self.done_pick_btn = QPushButton("🔍 Seleccionar...")
        self.active_auto_pick_btn = QPushButton("🔍 Seleccionar...")
        self.done_auto_pick_btn = QPushButton("🔍 Seleccionar...")
        self.active_target_combo = QComboBox()
        self.done_target_combo = QComboBox()

    def set_controller(self, controller):
        self.controller = controller
        if hasattr(self, "active_conditions_widget"):
            self.active_conditions_widget.set_controller(controller)
            self.exit_conditions_widget.set_controller(controller)
        self.refresh_effects_list()

    def set_lore_block(self, block: Optional[LoreBlock]):
        self._loading = True
        try:
            self._set_lore_block_internal(block)
        finally:
            self._loading = False

    def _set_lore_block_internal(self, block: Optional[LoreBlock]):
        self.lore_block = block
        self.active_conditions_widget.set_controller(self.controller)
        self.exit_conditions_widget.set_controller(self.controller)

        self.populate_parent_combo(block.id if block else None)

        if not block:
            self.id_edit.clear()
            self.title_edit.clear()
            self.desc_edit.clear()
            idx_ev = self.preset_combo.findData("event")
            if idx_ev >= 0:
                self.preset_combo.setCurrentIndex(idx_ev)
            self._apply_preset_styling("event")
            self.active_conditions_widget.set_conditions([])
            self.exit_conditions_widget.set_conditions([])
            self.refresh_effects_list()
            return

        preset_val = getattr(block, "preset", "event") or "event"
        idx_preset = self.preset_combo.findData(preset_val)
        if idx_preset >= 0:
            self.preset_combo.setCurrentIndex(idx_preset)
        else:
            idx_ev = self.preset_combo.findData("event")
            if idx_ev >= 0:
                self.preset_combo.setCurrentIndex(idx_ev)
        self._apply_preset_styling(preset_val)

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

        # Condiciones Active
        self.active_conditions_widget.set_conditions(block.conditions or [])
        self.rag_active_check.setChecked(block.rag_enabled)
        self.phrases_edit.setPlainText("\n".join(block.trigger_phrases or []))
        self.phrases_edit.setEnabled(block.rag_enabled)

        # Condiciones Done
        self.exit_conditions_widget.set_conditions(block.exit_conditions or [])
        exit_rag = getattr(block, "exit_rag_enabled", False)
        self.rag_exit_check.setChecked(exit_rag)
        exit_phrases = getattr(block, "exit_trigger_phrases", []) or []
        self.exit_phrases_edit.setPlainText("\n".join(exit_phrases))
        self.exit_phrases_edit.setEnabled(exit_rag)

        # Rellenar combos de compatibilidad si existen
        self.populate_target_combo(self.active_target_combo, block.on_active.target if block else None)
        self.populate_target_combo(self.done_target_combo, block.on_done.target if block else None)

        # Cargar lista interactiva de efectos
        self.refresh_effects_list()

    def refresh_effects_list(self):
        """Reconstruye visualmente la lista de tarjetas de efectos."""
        while self.effects_container_layout.count():
            item = self.effects_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.lore_block or not self.lore_block.effects:
            empty_lbl = QLabel("No hay efectos definidos para este LoreBlock.\nHaz clic en '➕ Añadir Efecto...' para configurar uno.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #888; font-style: italic; padding: 24px; font-size: 12px;")
            self.effects_container_layout.addWidget(empty_lbl)
            return

        for idx, eff in enumerate(self.lore_block.effects):
            card = self._create_effect_card(idx, eff)
            self.effects_container_layout.addWidget(card)

    def _create_effect_card(self, index: int, eff: LoreEffects) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #cfcfcf;
                border-radius: 5px;
                padding: 6px 10px;
            }
            QFrame:hover {
                background: #f0f7ff;
                border-color: #3399ff;
            }
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Distintivo de Momento (Active vs Done)
        timing_badge = QLabel()
        timing_badge.setStyleSheet("padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        if eff.timing == "active":
            timing_badge.setText("🟢 Al pasar a Active")
            timing_badge.setStyleSheet(timing_badge.styleSheet() + "background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;")
        else:
            timing_badge.setText("🔵 Al pasar a Done")
            timing_badge.setStyleSheet(timing_badge.styleSheet() + "background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb;")
        layout.addWidget(timing_badge)

        # Distintivo de Entidad Objetivo
        target_badge = QLabel()
        target_badge.setStyleSheet("padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background: #f5f5f5; color: #333; border: 1px solid #e0e0e0;")
        badge_text, _ = self._resolve_entity_badge(eff.target)
        target_badge.setText(badge_text)
        layout.addWidget(target_badge)

        # Contenido central: Directiva y/o Mutaciones
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)

        if eff.directive:
            dir_snip = eff.directive[:65] + "..." if len(eff.directive) > 65 else eff.directive
            dir_lbl = QLabel(f"<i>&ldquo;{dir_snip}&rdquo;</i>")
            dir_lbl.setStyleSheet("color: #444; font-size: 11px;")
            details_layout.addWidget(dir_lbl)

        mut_tags = self._format_card_mutations(eff)
        if mut_tags:
            mut_lbl = QLabel("  •  ".join(mut_tags))
            mut_lbl.setStyleSheet("color: #0d47a1; font-size: 11px; font-weight: bold;")
            details_layout.addWidget(mut_lbl)
        elif not eff.directive:
            none_lbl = QLabel("<i>(Sin directiva ni mutaciones adicionales)</i>")
            none_lbl.setStyleSheet("color: #999; font-size: 11px;")
            details_layout.addWidget(none_lbl)

        layout.addLayout(details_layout, 1)

        # Botones de acción
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.setToolTip("Editar este efecto")
        edit_btn.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        edit_btn.clicked.connect(lambda _, i=index: self.on_edit_effect_clicked(i))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setToolTip("Eliminar este efecto")
        del_btn.setStyleSheet("""
            QPushButton {
                color: #cc0000;
                font-size: 11px;
                padding: 3px 6px;
                border: 1px solid #ffcccc;
                border-radius: 3px;
                background: #fff5f5;
            }
            QPushButton:hover {
                background: #ffe6e6;
                border-color: #cc0000;
            }
        """)
        del_btn.clicked.connect(lambda _, i=index: self.on_delete_effect_clicked(i))
        layout.addWidget(del_btn)

        # Doble clic en la tarjeta para editar
        card.mouseDoubleClickEvent = lambda event, i=index: self.on_edit_effect_clicked(i)

        return card

    def _resolve_entity_badge(self, target_id: Optional[str]) -> Tuple[str, str]:
        """Devuelve (texto_badge, tipo) para la entidad objetivo."""
        if not target_id or not str(target_id).strip():
            return "🌐 Global / Sin objetivo", "global"

        tid = str(target_id).strip()
        if self.controller:
            npcs = getattr(self.controller, "get_all_npcs", lambda: [])() or getattr(self.controller, "get_npcs", lambda: [])()
            for n in npcs:
                if n.id == tid or n.name == tid:
                    return f"👤 {n.name} ({n.id})", "npc"

            places = getattr(self.controller, "get_all_places", lambda: [])()
            for p in places:
                if p.id == tid or p.name == tid:
                    return f"📍 {p.name} ({p.id})", "place"

            objs = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
            for o in objs:
                if o.id == tid or o.name == tid:
                    return f"📦 {o.name} ({o.id})", "item"

            lbs = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])
            for lb in lbs:
                if lb.id == tid:
                    title = lb.title or lb.name or lb.id
                    return f"📜 {title} ({lb.id})", "loreblock"

        return f"🔹 {tid}", "custom"

    def _format_card_mutations(self, eff: LoreEffects) -> List[str]:
        tags = []
        delta = eff.gold_delta if eff.gold_delta != 0 else (eff.give_gold - eff.take_gold)
        if delta != 0:
            tags.append(f"💰 {delta:+d} Oro")
        if eff.affinity_delta != 0.0:
            tags.append(f"❤️ {eff.affinity_delta:+.2f} Afinidad")
        for it in eff.give_items:
            tags.append(f"🎁 +{it}")
        for it in eff.take_items:
            tags.append(f"📤 -{it}")
        for blk in eff.block_connections:
            tags.append(f"🚫 Bloquea: {blk}")
        for alw in eff.allow_connections:
            tags.append(f"🟢 Abre: {alw}")
        if eff.force_action or eff.trigger_action_type:
            act = eff.trigger_action_type or "TALK"
            tgt = eff.trigger_action_target or eff.target or ""
            tags.append(f"⚡ {act} -> {tgt}")
        if getattr(eff, "bypass_llm", False):
            tags.append("⚡ Bypass LLM")
        mode = getattr(eff, "execution_mode", "push")
        if mode == "hook":
            tags.append("🎧 Hook")
        elif mode == "push" and not (eff.force_action or eff.trigger_action_type):
            tags.append("⚡ Push")
        return tags

    def on_add_effect_clicked(self):
        if not self.lore_block:
            return
        dialog = LoreEffectDialog(controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_eff = dialog.get_effect()
            self.lore_block.effects.append(new_eff)
            self.refresh_effects_list()
            self.lore_changed.emit()

    def on_edit_effect_clicked(self, index: int):
        if not self.lore_block or index < 0 or index >= len(self.lore_block.effects):
            return
        dialog = LoreEffectDialog(effect=self.lore_block.effects[index], controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_eff = dialog.get_effect()
            self.lore_block.effects[index] = updated_eff
            self.refresh_effects_list()
            self.lore_changed.emit()

    def on_delete_effect_clicked(self, index: int):
        if not self.lore_block or index < 0 or index >= len(self.lore_block.effects):
            return
        self.lore_block.effects.pop(index)
        self.refresh_effects_list()
        self.lore_changed.emit()

    def populate_target_combo(self, combo: QComboBox, current_value: Optional[str] = None):
        """Rellena un selector de objetivo con todas las entidades disponibles (retrocompatibilidad)."""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(Ninguno - Solo Estado / Sin Objetivo)", "")

        if self.controller:
            npcs = getattr(self.controller, "get_all_npcs", lambda: [])() or getattr(self.controller, "get_npcs", lambda: [])()
            for n in npcs:
                combo.addItem(f"👤 {n.name} ({n.id})", n.id)

            places = getattr(self.controller, "get_all_places", lambda: [])()
            for p in places:
                combo.addItem(f"📍 {p.name} ({p.id})", p.id)

            objs = getattr(self.controller, "get_objects", lambda: [])() or getattr(self.controller, "objects", [])
            for o in objs:
                combo.addItem(f"📦 {o.name} ({o.id})", o.id)

        if current_value:
            idx = combo.findData(current_value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                for i in range(combo.count()):
                    if current_value.lower() in combo.itemText(i).lower():
                        combo.setCurrentIndex(i)
                        break
                else:
                    combo.addItem(f"🔹 {current_value} (Personalizado)", current_value)
                    combo.setCurrentIndex(combo.count() - 1)
        else:
            combo.setCurrentIndex(0)

        combo.blockSignals(False)

    def on_pick_effect_target(self, prefix: str):
        """Abre el diálogo modal de selección de entidades (retrocompatibilidad)."""
        target_combo = getattr(self, f"{prefix}_target_combo", self.active_target_combo)
        current_target = target_combo.currentData() or ""

        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=["place", "npc", "item", "loreblock"],
            mode="entity_only",
            initial_entity_id=current_target,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = dialog.get_selected_entity_id()
            if selected_id:
                idx = target_combo.findData(selected_id)
                if idx >= 0:
                    target_combo.setCurrentIndex(idx)
                else:
                    selected_name = dialog.get_selected_entity_name() or selected_id
                    etype = dialog.get_selected_entity_type()
                    emoji = EntityPickerDialog.TYPE_EMOJIS.get(etype, "🔹")
                    target_combo.addItem(f"{emoji} {selected_name} ({selected_id})", selected_id)
                    target_combo.setCurrentIndex(target_combo.count() - 1)

                if self.lore_block:
                    if prefix == "active":
                        self.lore_block.on_active.target = selected_id
                    else:
                        self.lore_block.on_done.target = selected_id
                    self.refresh_effects_list()
                    self.lore_changed.emit()

    def populate_parent_combo(self, current_id: Optional[str]):
        self.parent_combo.blockSignals(True)
        self.parent_combo.clear()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")

        if not self.controller:
            self.parent_combo.blockSignals(False)
            return

        all_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])

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

    def _apply_preset_styling(self, preset: str):
        PRESET_TITLES = {
            "chapter": ("📖", "Capítulo", "#2b6cb0"),
            "quest": ("⚔️", "Quest (Misión)", "#b7791f"),
            "task": ("📌", "Tarea (Objetivo)", "#2c7a7b"),
            "event_diag": ("💬", "Evento de Diálogo", "#4a5568"),
            "event_look": ("👁️", "Evento de Inspección", "#4a5568"),
            "event_popup": ("📢", "Pop-up Informativo", "#c53030"),
            "event": ("⚡", "Evento Libre", "#5c6bc0"),
        }
        icon, label, color = PRESET_TITLES.get(preset, ("📜", "Bloque de Lore", "#5c6bc0"))
        self.header_title.setText(f"<b>{icon} {label} (HSM)</b>")
        self.header_title.setStyleSheet(f"font-size: 14px; color: {color};")

    def on_preset_changed(self):
        if not self.lore_block or getattr(self, "_loading", False):
            return
        preset_val = self.preset_combo.currentData() or "event"
        self.lore_block.preset = preset_val
        self._apply_preset_styling(preset_val)
        if self.parent_app and hasattr(self.parent_app, "refresh_tree"):
            self.parent_app.refresh_tree()
        self.on_field_changed()

    def on_title_changed(self, text: str):
        if not self.lore_block or getattr(self, "_loading", False):
            return
        self.lore_block.title = text
        self.lore_block.name = text
        if self.parent_app and hasattr(self.parent_app, "update_selected_tree_item_text"):
            self.parent_app.update_selected_tree_item_text(text)

    def on_parent_changed(self):
        if not self.lore_block or getattr(self, "_loading", False):
            return
        p_val = self.parent_combo.currentData()
        self.lore_block.parent_id = str(p_val).strip() if p_val and str(p_val).strip() else None
        if self.parent_app and hasattr(self.parent_app, "refresh_tree"):
            self.parent_app.refresh_tree()

    def on_active_conditions_changed(self):
        if not self.lore_block or getattr(self, "_loading", False):
            return
        self.lore_block.conditions = self.active_conditions_widget.get_conditions()
        self.on_field_changed()

    def on_exit_conditions_changed(self):
        if not self.lore_block or getattr(self, "_loading", False):
            return
        self.lore_block.exit_conditions = self.exit_conditions_widget.get_conditions()
        self.on_field_changed()

    def on_rag_active_toggled(self, checked: bool):
        if getattr(self, "_loading", False):
            return
        self.phrases_edit.setEnabled(checked)
        if self.lore_block:
            self.lore_block.rag_enabled = checked
            self.lore_block.trigger_mode = "reactive" if checked else "proactive"
        self.on_field_changed()

    def on_rag_exit_toggled(self, checked: bool):
        if getattr(self, "_loading", False):
            return
        self.exit_phrases_edit.setEnabled(checked)
        if self.lore_block:
            self.lore_block.exit_rag_enabled = checked
        self.on_field_changed()

    def on_field_changed(self):
        if not self.lore_block or getattr(self, "_loading", False):
            return

        self.lore_block.id = self.id_edit.text().strip()
        self.lore_block.preset = self.preset_combo.currentData() or "event"
        self.lore_block.description = self.desc_edit.toPlainText().strip()

        phrases = [p.strip() for p in self.phrases_edit.toPlainText().split("\n") if p.strip()]
        self.lore_block.trigger_phrases = phrases

        exit_phrases = [p.strip() for p in self.exit_phrases_edit.toPlainText().split("\n") if p.strip()]
        self.lore_block.exit_trigger_phrases = exit_phrases

        self.lore_changed.emit()

    def on_delete_clicked(self):
        if self.lore_block and self.parent_app and hasattr(self.parent_app, "delete_lore_block"):
            self.parent_app.delete_lore_block(self.lore_block)

