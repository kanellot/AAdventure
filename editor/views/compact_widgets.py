"""Widgets compactos estilizados para sustituir tablas pesadas en formularios.

Incluye:
- CompactConditionListWidget: Visualizador/editor de condiciones en formato fichas (chips).
- CompactEntityListWidget: Visualizador/editor de listas de entidades (visible_entities, target_entities).
- LoreReferenceListWidget: Visor de LoreBlocks vinculados con distintivos de origen y soporte para doble clic.
"""

from typing import List, Optional, Tuple, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from domains.lore import EntityCondition
from editor.views.entity_picker import EntityPickerDialog


TYPE_EMOJIS = {
    "place": "📍",
    "npc": "👤",
    "item": "📦",
    "loreblock": "📜",
}


class CompactConditionListWidget(QWidget):
    """
    Lista compacta de condiciones (AND) representada mediante tarjetas horizontales limpias.
    Reemplaza a QTableWidget ocupando mucho menos espacio y con mejor legibilidad.
    """

    conditions_changed = Signal()

    def __init__(self, controller=None, allowed_types: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.allowed_types = allowed_types or ["place", "npc", "item", "loreblock"]
        self.conditions: List[EntityCondition] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Botón de añadir
        top_bar = QHBoxLayout()
        self.add_btn = QPushButton("➕ Añadir Condición...")
        self.add_btn.setStyleSheet("padding: 4px 10px; font-weight: bold;")
        self.add_btn.clicked.connect(self.on_add_condition)
        top_bar.addWidget(self.add_btn)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # Área con scroll para las fichas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(160)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(4)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        self.empty_label = QLabel("No hay condiciones definidas (se cumple automáticamente).")
        self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
        self.container_layout.addWidget(self.empty_label)

    def set_controller(self, controller):
        self.controller = controller

    def set_conditions(self, conditions: List[EntityCondition]):
        self.conditions = list(conditions or [])
        self.refresh_chips()

    def get_conditions(self) -> List[EntityCondition]:
        return self.conditions

    def refresh_chips(self):
        # Limpiar chips anteriores
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.conditions:
            self.empty_label = QLabel("No hay condiciones definidas (se cumple automáticamente).")
            self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
            self.container_layout.addWidget(self.empty_label)
            return

        for idx, cond in enumerate(self.conditions):
            chip = self._create_condition_chip(idx, cond)
            self.container_layout.addWidget(chip)

    def _resolve_entity_name(self, etype: str, eid: str) -> str:
        if not self.controller:
            return eid
        if etype == "place":
            p = self.controller.get_place_by_id(eid) or self.controller.get_place_by_name(eid)
            return p.name if p else eid
        elif etype == "npc":
            n = self.controller.get_npc_by_id(eid)
            return n.name if n else eid
        elif etype == "item":
            if eid == "gold":
                return "Monedas de Oro"
            obj = self.controller.get_object_by_id(eid)
            return obj.name if obj else eid
        elif etype == "loreblock":
            b = self.controller.get_lore_block_by_id(eid)
            return b.title or b.name or eid if b else eid
        return eid

    def _create_condition_chip(self, index: int, cond: EntityCondition) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QFrame:hover {
                border-color: #0078d7;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Indicador NOT
        if cond.is_negated:
            not_badge = QLabel("⛔ NOT")
            not_badge.setStyleSheet("color: #d9534f; font-weight: bold; font-size: 11px;")
            layout.addWidget(not_badge)

        # Emoji y Entidad
        emoji = TYPE_EMOJIS.get(cond.entity_type, "🔹")
        name = self._resolve_entity_name(cond.entity_type, cond.entity_id)
        ent_label = QLabel(f"<b>{emoji} {name}</b>")
        layout.addWidget(ent_label)

        # Flecha
        arrow = QLabel("➔")
        arrow.setStyleSheet("color: #666;")
        layout.addWidget(arrow)

        # Subcondición y valor
        val_str = ""
        if cond.value is not None:
            if cond.sub_condition == "affinity":
                val_str = f" ≥ {float(cond.value):.2f}"
            elif cond.entity_id == "gold":
                val_str = f" ≥ {int(cond.value)}"
            else:
                val_str = f" = {cond.value}"

        sub_label = QLabel(f"<code>{cond.sub_condition}</code>{val_str}")
        sub_label.setStyleSheet("color: #333;")
        layout.addWidget(sub_label)

        layout.addStretch()

        # Botón Editar
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Editar condición")
        edit_btn.setStyleSheet("border: none; background: transparent; padding: 2px;")
        edit_btn.clicked.connect(lambda _, i=index: self.on_edit_condition(i))
        layout.addWidget(edit_btn)

        # Botón Eliminar
        del_btn = QPushButton("✕")
        del_btn.setToolTip("Eliminar condición")
        del_btn.setStyleSheet("border: none; background: transparent; color: #cc0000; font-weight: bold; padding: 2px;")
        del_btn.clicked.connect(lambda _, i=index: self.on_delete_condition(i))
        layout.addWidget(del_btn)

        frame.setCursor(Qt.PointingHandCursor)
        frame.mouseDoubleClickEvent = lambda event, i=index: self.on_edit_condition(i)

        return frame

    def on_add_condition(self):
        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=self.allowed_types,
            mode="condition",
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_cond = dialog.get_condition()
            self.conditions.append(new_cond)
            self.refresh_chips()
            self.conditions_changed.emit()

    def on_edit_condition(self, index: int):
        if index < 0 or index >= len(self.conditions):
            return
        cond = self.conditions[index]
        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=self.allowed_types,
            mode="condition",
            initial_condition=cond,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.conditions[index] = dialog.get_condition()
            self.refresh_chips()
            self.conditions_changed.emit()

    def on_delete_condition(self, index: int):
        if index < 0 or index >= len(self.conditions):
            return
        self.conditions.pop(index)
        self.refresh_chips()
        self.conditions_changed.emit()


class CompactEntityListWidget(QWidget):
    """
    Contenedor compacto de entidades seleccionadas (ej. visible_entities o target_entities).
    Muestra fichas compactas con su emoji representativo y botón para eliminar.
    """

    entities_changed = Signal()

    def __init__(self, controller=None, allowed_types: Optional[List[str]] = None, button_text="➕ Añadir Entidad...", parent=None):
        super().__init__(parent)
        self.controller = controller
        self.allowed_types = allowed_types or ["place", "npc", "item"]
        self.entity_ids: List[str] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        top_bar = QHBoxLayout()
        self.add_btn = QPushButton(button_text)
        self.add_btn.setStyleSheet("padding: 3px 8px;")
        self.add_btn.clicked.connect(self.on_add_entity)
        top_bar.addWidget(self.add_btn)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(130)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(4)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        self.empty_label = QLabel("Ninguna entidad seleccionada.")
        self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
        self.container_layout.addWidget(self.empty_label)

    def set_controller(self, controller):
        self.controller = controller

    def set_entity_ids(self, entity_ids: List[str]):
        self.entity_ids = list(entity_ids or [])
        self.refresh_chips()

    def get_entity_ids(self) -> List[str]:
        return self.entity_ids

    def _resolve_entity(self, eid: str) -> Tuple[str, str]:
        """Retorna (emoji, nombre)."""
        if not self.controller:
            return ("🔹", eid)

        # 1. Probar Place
        p = self.controller.get_place_by_id(eid) or self.controller.get_place_by_name(eid)
        if p:
            return ("📍", p.name)

        # 2. Probar NPC
        n = self.controller.get_npc_by_id(eid)
        if n:
            return ("👤", n.name)

        # 3. Probar Objeto
        o = self.controller.get_object_by_id(eid)
        if o:
            return ("📦", o.name)

        # 4. Probar LoreBlock
        b = self.controller.get_lore_block_by_id(eid)
        if b:
            return ("📜", b.title or b.name or b.id)

        return ("🔹", eid)

    def refresh_chips(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.entity_ids:
            self.empty_label = QLabel("Ninguna entidad seleccionada.")
            self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
            self.container_layout.addWidget(self.empty_label)
            return

        for idx, eid in enumerate(self.entity_ids):
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background: #ffffff;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
            """)
            layout = QHBoxLayout(chip)
            layout.setContentsMargins(4, 2, 4, 2)

            emoji, name = self._resolve_entity(eid)
            label = QLabel(f"{emoji} <b>{name}</b> <span style='color: #666;'>({eid})</span>")
            layout.addWidget(label)
            layout.addStretch()

            del_btn = QPushButton("✕")
            del_btn.setToolTip("Quitar entidad")
            del_btn.setStyleSheet("border: none; background: transparent; color: #cc0000; font-weight: bold; padding: 2px;")
            del_btn.clicked.connect(lambda _, i=idx: self.on_remove_entity(i))
            layout.addWidget(del_btn)

            self.container_layout.addWidget(chip)

    def on_add_entity(self):
        dialog = EntityPickerDialog(
            controller=self.controller,
            allowed_types=self.allowed_types,
            mode="entity_only",
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = dialog.get_selected_entity_id()
            if selected_id and selected_id not in self.entity_ids:
                self.entity_ids.append(selected_id)
                self.refresh_chips()
                self.entities_changed.emit()

    def on_remove_entity(self, index: int):
        if 0 <= index < len(self.entity_ids):
            self.entity_ids.pop(index)
            self.refresh_chips()
            self.entities_changed.emit()


class LoreReferenceListWidget(QWidget):
    """
    Visor de referencias a LoreBlocks vinculados con distintivos enriquecidos por emojis:
    - 📍 Directo
    - 👤 Vía: <NPC>
    - 📦 Vía: <Objeto>
    
    Al hacer doble clic en una fila, emite la señal lore_block_requested(lb_id)
    para saltar inmediatamente a su edición en el árbol y formulario principal.
    """

    lore_block_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdcdc; border-radius: 4px; background: #fafafa; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(4)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        self.empty_label = QLabel("No hay LoreBlocks vinculados a esta entidad.")
        self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 6px;")
        self.container_layout.addWidget(self.empty_label)

    def set_references(self, refs: List[Tuple[str, str, str, str]]):
        """
        refs es una lista de tuplas:
        (lb_id, lb_title, origin_type, origin_name)
        origin_type: 'direct', 'npc', 'item'
        """
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not refs:
            self.empty_label = QLabel("No hay LoreBlocks vinculados a esta entidad.")
            self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 6px;")
            self.container_layout.addWidget(self.empty_label)
            return

        for lb_id, lb_title, orig_type, orig_name in refs:
            card = self._create_card(lb_id, lb_title, orig_type, orig_name)
            self.container_layout.addWidget(card)

    def _create_card(self, lb_id: str, title: str, orig_type: str, orig_name: str) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #cfcfcf;
                border-radius: 5px;
                padding: 4px 8px;
            }
            QFrame:hover {
                background: #eef7ff;
                border-color: #3399ff;
            }
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Distintivo de Origen
        badge = QLabel()
        badge.setStyleSheet("padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;")
        if orig_type == "direct":
            badge.setText("📍 Directo")
            badge.setStyleSheet(badge.styleSheet() + "background: #e1f0fa; color: #0066cc; border: 1px solid #b3d7f2;")
        elif orig_type == "npc":
            badge.setText(f"👤 Vía: {orig_name}")
            badge.setStyleSheet(badge.styleSheet() + "background: #eafaf1; color: #1e824c; border: 1px solid #a9dfbf;")
        elif orig_type == "item":
            badge.setText(f"📦 Vía: {orig_name}")
            badge.setStyleSheet(badge.styleSheet() + "background: #fef5e7; color: #d35400; border: 1px solid #f8c471;")
        else:
            badge.setText(f"🔹 {orig_name}")
            badge.setStyleSheet(badge.styleSheet() + "background: #f2f2f2; color: #555;")
        layout.addWidget(badge)

        # Título del LoreBlock
        title_label = QLabel(f"<b>📜 {title}</b> <span style='color: #666;'>({lb_id})</span>")
        layout.addWidget(title_label)

        layout.addStretch()

        hint = QLabel("<i>(Doble clic para editar)</i>")
        hint.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(hint)

        # Doble clic en la tarjeta
        card.mouseDoubleClickEvent = lambda event, target_id=lb_id: self.lore_block_requested.emit(target_id)

        return card
