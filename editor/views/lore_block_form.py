"""Formulario central para la edición completa de un Bloque de Lore (HSM):
1. Pestaña General: ID, Título, Descripción, Bloque Padre HSM (📁), Estado y Entidades Afectadas.
2. Pestaña Condiciones Active: Condiciones de estado previas y Antenas RAG de activación.
3. Pestaña Condiciones Done: Repetición, Condiciones de estado de salida y Antenas RAG de finalización.
4. Pestaña Efectos: Directiva para el LLM y mutaciones del Gamestate (oro, afinidad, inventario, desbloqueos).
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTabWidget, QMessageBox, QPushButton
)
from PySide6.QtCore import Qt, Signal
from domains.lore import LoreBlock, LoreEffects
from editor.views.compact_widgets import CompactConditionListWidget, CompactEntityListWidget


class LoreBlockForm(QWidget):
    """Formulario integral para la configuración de un LoreBlock (HSM)."""

    lore_changed = Signal()

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
        # PESTAÑA 1: General y Entidades Afectadas
        # =====================================================================
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)

        props_group = QGroupBox("Propiedades Generales del LoreBlock")
        props_form = QFormLayout(props_group)

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
        self.desc_edit.setMaximumHeight(65)
        self.desc_edit.textChanged.connect(self.on_field_changed)
        props_form.addRow("Descripción:", self.desc_edit)

        self.parent_combo = QComboBox()
        self.parent_combo.currentIndexChanged.connect(self.on_parent_changed)
        props_form.addRow("Carpeta / Bloque Padre (HSM):", self.parent_combo)

        self.state_combo = QComboBox()
        self.state_combo.addItem("⚪ Unknown (No descubierto)", "unknown")
        self.state_combo.addItem("🟢 Active (Activo / Abierto)", "active")
        self.state_combo.addItem("🔵 Done (Completado / Resuelto)", "done")
        self.state_combo.currentIndexChanged.connect(self.on_field_changed)
        props_form.addRow("Estado del Bloque:", self.state_combo)

        gen_layout.addWidget(props_group)

        # Selector de Entidades Afectadas (target_entities)
        target_group = QGroupBox("Entidades Afectadas (Inyección de directiva en diálogo o inspección)")
        target_vbox = QVBoxLayout(target_group)
        self.targets_widget = CompactEntityListWidget(
            controller=self.controller,
            allowed_types=["place", "npc", "item"],
            button_text="➕ Añadir Objetivo Afectado...",
            parent=self
        )
        self.targets_widget.entities_changed.connect(self.on_targets_changed)
        target_vbox.addWidget(self.targets_widget)
        gen_layout.addWidget(target_group)

        self.tab_widget.addTab(self.tab_general, "General")

        # =====================================================================
        # PESTAÑA 2: Condiciones Active
        # =====================================================================
        self.tab_active = QWidget()
        active_layout = QVBoxLayout(self.tab_active)

        # Sección 1: Condiciones de Estado (Requisito Previo Obligatorio)
        cond_group = QGroupBox("1. Condiciones de Estado (Primera Autoridad - Requisito Previo)")
        cond_vbox = QVBoxLayout(cond_group)
        cond_desc = QLabel(
            "El bloque solo evaluará las antenas semánticas cuando TODAS estas condiciones "
            "se cumplan conjuntamente (AND)."
        )
        cond_desc.setStyleSheet("color: #444; font-size: 11px;")
        cond_vbox.addWidget(cond_desc)

        self.active_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=self)
        self.active_conditions_widget.conditions_changed.connect(self.on_active_conditions_changed)
        cond_vbox.addWidget(self.active_conditions_widget)
        active_layout.addWidget(cond_group)

        # Sección 2: Antenas RAG de Activación
        rag_group = QGroupBox("2. Antenas Semánticas RAG de Activación (Opcional)")
        rag_vbox = QVBoxLayout(rag_group)

        self.rag_active_check = QCheckBox("Habilitar antenas semánticas (vigilar solo si se cumplen las condiciones previas)")
        self.rag_active_check.toggled.connect(self.on_rag_active_toggled)
        rag_vbox.addWidget(self.rag_active_check)

        self.phrases_edit = QTextEdit()
        self.phrases_edit.setPlaceholderText("Introduce una frase gatillo por línea (ej: ¿Has visto al nigromante?)...")
        self.phrases_edit.setMaximumHeight(80)
        self.phrases_edit.textChanged.connect(self.on_field_changed)
        rag_vbox.addWidget(self.phrases_edit)

        rag_note = QLabel("<i>Si las antenas están desactivadas, el bloque se activará automáticamente al cumplir las condiciones.</i>")
        rag_note.setStyleSheet("color: #666; font-size: 11px;")
        rag_vbox.addWidget(rag_note)
        active_layout.addWidget(rag_group)

        self.tab_widget.addTab(self.tab_active, "Condiciones Active")

        # =====================================================================
        # PESTAÑA 3: Condiciones Done
        # =====================================================================
        self.tab_done = QWidget()
        done_layout = QVBoxLayout(self.tab_done)

        # Ciclo de Repetición
        loop_group = QGroupBox("Ciclo de Vida y Repetición")
        loop_vbox = QVBoxLayout(loop_group)
        self.repeatable_check = QCheckBox("Repetir LoreBlock (permanecer en Active en lugar de concluir automáticamente)")
        self.repeatable_check.toggled.connect(self.on_repeatable_toggled)
        loop_vbox.addWidget(self.repeatable_check)
        done_layout.addWidget(loop_group)

        # Sección 1: Condiciones de Salida
        exit_group = QGroupBox("1. Condiciones de Salida (Primera Autoridad - Requisito Previo)")
        exit_vbox = QVBoxLayout(exit_group)
        exit_desc = QLabel(
            "Condiciones de estado necesarias para dar por finalizado el bloque y transicionar a Done."
        )
        exit_desc.setStyleSheet("color: #444; font-size: 11px;")
        exit_vbox.addWidget(exit_desc)

        self.exit_conditions_widget = CompactConditionListWidget(controller=self.controller, parent=self)
        self.exit_conditions_widget.conditions_changed.connect(self.on_exit_conditions_changed)
        exit_vbox.addWidget(self.exit_conditions_widget)
        done_layout.addWidget(exit_group)

        # Sección 2: Antenas RAG de Finalización
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

        exit_note = QLabel("<i>Si están desactivadas, transicionará a Done automáticamente al cumplirse las condiciones de salida.</i>")
        exit_note.setStyleSheet("color: #666; font-size: 11px;")
        rag_exit_vbox.addWidget(exit_note)
        done_layout.addWidget(rag_exit_group)

        self.tab_widget.addTab(self.tab_done, "Condiciones Done")

        # =====================================================================
        # PESTAÑA 4: Efectos
        # =====================================================================
        self.tab_effects = QWidget()
        eff_layout = QVBoxLayout(self.tab_effects)

        # Directiva
        dir_group = QGroupBox("Directiva para el Modelo de Lenguaje (LLM / Dungeon Master)")
        dir_vbox = QVBoxLayout(dir_group)
        self.directive_edit = QTextEdit()
        self.directive_edit.setPlaceholderText("Instrucción narrativa estricta inyectada al contexto...")
        self.directive_edit.setMaximumHeight(85)
        self.directive_edit.textChanged.connect(self.on_field_changed)
        dir_vbox.addWidget(self.directive_edit)
        eff_layout.addWidget(dir_group)

        # Mutaciones al Gamestate
        eff_group = QGroupBox("Efectos sobre el Estado del Juego")
        eff_form = QFormLayout(eff_group)

        self.timing_combo = QComboBox()
        self.timing_combo.addItem("Al activarse el bloque (on_active)", "on_active")
        self.timing_combo.addItem("Al completarse y pasar a Done (on_done)", "on_done")
        self.timing_combo.currentIndexChanged.connect(self.on_field_changed)
        eff_form.addRow("Momento de Aplicación:", self.timing_combo)

        row_deltas = QHBoxLayout()
        self.gold_spin = QSpinBox()
        self.gold_spin.setRange(-99999, 99999)
        self.gold_spin.valueChanged.connect(self.on_field_changed)
        row_deltas.addWidget(QLabel("💰 Oro (+/-):"))
        row_deltas.addWidget(self.gold_spin)

        self.affinity_spin = QDoubleSpinBox()
        self.affinity_spin.setRange(-1.0, 1.0)
        self.affinity_spin.setSingleStep(0.05)
        self.affinity_spin.valueChanged.connect(self.on_field_changed)
        row_deltas.addWidget(QLabel("❤️ Afinidad (+/-):"))
        row_deltas.addWidget(self.affinity_spin)
        eff_form.addRow(row_deltas)

        eff_layout.addWidget(eff_group)

        # Objetos y Entidades Desbloqueadas (con selectores limpios)
        items_group = QGroupBox("Objetos Modificados en el Inventario")
        items_layout = QHBoxLayout(items_group)

        give_vbox = QVBoxLayout()
        give_vbox.addWidget(QLabel("<b>Entregar al Jugador:</b>"))
        self.give_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Entregar Objeto...", parent=self
        )
        self.give_items_widget.entities_changed.connect(self.on_field_changed)
        give_vbox.addWidget(self.give_items_widget)
        items_layout.addLayout(give_vbox)

        take_vbox = QVBoxLayout()
        take_vbox.addWidget(QLabel("<b>Retirar del Jugador:</b>"))
        self.take_items_widget = CompactEntityListWidget(
            controller=self.controller, allowed_types=["item"], button_text="➕ Retirar Objeto...", parent=self
        )
        self.take_items_widget.entities_changed.connect(self.on_field_changed)
        take_vbox.addWidget(self.take_items_widget)
        items_layout.addLayout(take_vbox)

        eff_layout.addWidget(items_group)

        self.tab_widget.addTab(self.tab_effects, "Efectos")

    def set_lore_block(self, block: Optional[LoreBlock]):
        self.lore_block = block
        self.targets_widget.set_controller(self.controller)
        self.active_conditions_widget.set_controller(self.controller)
        self.exit_conditions_widget.set_controller(self.controller)
        self.give_items_widget.set_controller(self.controller)
        self.take_items_widget.set_controller(self.controller)

        self.populate_parent_combo(block.id if block else None)

        if not block:
            self.id_edit.clear()
            self.title_edit.clear()
            self.desc_edit.clear()
            self.targets_widget.set_entity_ids([])
            self.active_conditions_widget.set_conditions([])
            self.exit_conditions_widget.set_conditions([])
            self.directive_edit.clear()
            return

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

        # Estado
        idx_st = self.state_combo.findData(block.state)
        if idx_st >= 0:
            self.state_combo.setCurrentIndex(idx_st)

        # Objetivos afectados
        self.targets_widget.set_entity_ids(block.target_entities or [])

        # Condiciones Active
        self.active_conditions_widget.set_conditions(block.conditions or [])
        self.rag_active_check.setChecked(block.rag_enabled)
        self.phrases_edit.setPlainText("\n".join(block.trigger_phrases or []))
        self.phrases_edit.setEnabled(block.rag_enabled)

        # Condiciones Done
        self.repeatable_check.setChecked(block.repeatable)
        self.exit_conditions_widget.set_conditions(block.exit_conditions or [])
        exit_rag = getattr(block, "exit_rag_enabled", False)
        self.rag_exit_check.setChecked(exit_rag)
        exit_phrases = getattr(block, "exit_trigger_phrases", []) or []
        self.exit_phrases_edit.setPlainText("\n".join(exit_phrases))
        self.exit_phrases_edit.setEnabled(exit_rag)

        # Efectos
        self.directive_edit.setPlainText(block.directive or "")
        idx_t = self.timing_combo.findData(block.effect_timing)
        if idx_t >= 0:
            self.timing_combo.setCurrentIndex(idx_t)

        delta = block.effects.gold_delta if block.effects.gold_delta != 0 else (block.effects.give_gold - block.effects.take_gold)
        self.gold_spin.setValue(delta)
        self.affinity_spin.setValue(block.effects.affinity_delta)

        self.give_items_widget.set_entity_ids(block.effects.give_items or [])
        self.take_items_widget.set_entity_ids(block.effects.take_items or [])

    def populate_parent_combo(self, current_id: Optional[str]):
        self.parent_combo.blockSignals(True)
        self.parent_combo.clear()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")

        if not self.controller:
            self.parent_combo.blockSignals(False)
            return

        all_blocks = getattr(self.controller, "get_lore_blocks", lambda: [])() or getattr(self.controller, "lore_blocks", [])

        # Excluir al bloque actual y a sus descendientes para evitar ciclos recursivos
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

    def on_title_changed(self, text: str):
        if self.lore_block:
            self.lore_block.title = text
            self.lore_block.name = text
            if self.parent_app and hasattr(self.parent_app, "update_selected_tree_item_text"):
                self.parent_app.update_selected_tree_item_text(text)

    def on_parent_changed(self):
        if self.lore_block:
            p_val = self.parent_combo.currentData()
            self.lore_block.parent_id = str(p_val).strip() if p_val and str(p_val).strip() else None
            if self.parent_app and hasattr(self.parent_app, "refresh_tree"):
                self.parent_app.refresh_tree()

    def on_targets_changed(self):
        if self.lore_block:
            self.lore_block.target_entities = self.targets_widget.get_entity_ids()

    def on_active_conditions_changed(self):
        if self.lore_block:
            self.lore_block.conditions = self.active_conditions_widget.get_conditions()

    def on_exit_conditions_changed(self):
        if self.lore_block:
            self.lore_block.exit_conditions = self.exit_conditions_widget.get_conditions()

    def on_rag_active_toggled(self, checked: bool):
        self.phrases_edit.setEnabled(checked)
        if self.lore_block:
            self.lore_block.rag_enabled = checked
            self.lore_block.trigger_mode = "reactive" if checked else "proactive"

    def on_rag_exit_toggled(self, checked: bool):
        self.exit_phrases_edit.setEnabled(checked)
        if self.lore_block:
            self.lore_block.exit_rag_enabled = checked

    def on_repeatable_toggled(self, checked: bool):
        if self.lore_block:
            self.lore_block.repeatable = checked

    def on_field_changed(self):
        if not self.lore_block:
            return

        self.lore_block.id = self.id_edit.text().strip()
        self.lore_block.description = self.desc_edit.toPlainText().strip()
        self.lore_block.state = self.state_combo.currentData()
        self.lore_block.directive = self.directive_edit.toPlainText().strip()
        self.lore_block.effect_timing = self.timing_combo.currentData()

        phrases = [p.strip() for p in self.phrases_edit.toPlainText().split("\n") if p.strip()]
        self.lore_block.trigger_phrases = phrases

        exit_phrases = [p.strip() for p in self.exit_phrases_edit.toPlainText().split("\n") if p.strip()]
        self.lore_block.exit_trigger_phrases = exit_phrases

        gold_val = self.gold_spin.value()
        give_gold = gold_val if gold_val > 0 else 0
        take_gold = abs(gold_val) if gold_val < 0 else 0

        self.lore_block.effects.give_items = self.give_items_widget.get_entity_ids()
        self.lore_block.effects.take_items = self.take_items_widget.get_entity_ids()
        self.lore_block.effects.gold_delta = gold_val
        self.lore_block.effects.give_gold = give_gold
        self.lore_block.effects.take_gold = take_gold
        self.lore_block.effects.affinity_delta = self.affinity_spin.value()

    def on_delete_clicked(self):
        if self.lore_block and self.parent_app and hasattr(self.parent_app, "delete_lore_block"):
            self.parent_app.delete_lore_block(self.lore_block)
