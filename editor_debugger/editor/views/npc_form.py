"""Formulario para editar las propiedades de un Personaje no Jugador (NPC):
1. Pestaña General: Datos básicos, lugar inicial (📍), estado y afinidad.
2. Pestaña Motivaciones: Gustos (likes) y aversiones (dislikes).
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QLabel,
    QDoubleSpinBox,
    QComboBox,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from domains import NPC


class NPCForm(QWidget):
    """Formulario para la edición integral de un Personaje no Jugador (NPC)."""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.npc: Optional[NPC] = None
        self.parent_app = parent

        # Layout Principal: Contiene el widget de pestañas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con botón de eliminar
        top_bar = QHBoxLayout()
        self.header_title = QLabel("<b>👤 Personaje (NPC)</b>")
        self.header_title.setStyleSheet("font-size: 14px; color: #2e7d32;")
        top_bar.addWidget(self.header_title)
        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar este personaje")
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
        # Pestaña 1: Datos Generales
        # =====================================================================
        self.tab_general = QWidget()
        general_layout = QFormLayout(self.tab_general)

        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold; color: #2e7d32;")
        general_layout.addRow("ID del NPC:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del personaje...")
        self.name_edit.textChanged.connect(self.on_name_changed)
        general_layout.addRow("Nombre del NPC:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Descripción física y rol del personaje...")
        self.desc_edit.setMaximumHeight(85)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        general_layout.addRow("Descripción:", self.desc_edit)

        self.initial_location_combo = QComboBox()
        self.initial_location_combo.currentTextChanged.connect(self.on_initial_location_changed)
        general_layout.addRow("Ubicación Inicial:", self.initial_location_combo)

        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("idle, ocupado, hostil, descansando...")
        self.state_edit.textChanged.connect(self.on_state_changed)
        general_layout.addRow("Estado del NPC (State):", self.state_edit)

        self.affinity_spin = QDoubleSpinBox()
        self.affinity_spin.setRange(0.0, 1.0)
        self.affinity_spin.setSingleStep(0.05)
        self.affinity_spin.valueChanged.connect(self.on_affinity_changed)
        general_layout.addRow("Afinidad Inicial (0.0 a 1.0):", self.affinity_spin)

        self.tab_widget.addTab(self.tab_general, "Datos Generales")

        # =====================================================================
        # Pestaña 2: Motivaciones
        # =====================================================================
        self.tab_motivations = QWidget()
        motivations_layout = QFormLayout(self.tab_motivations)

        self.likes_edit = QLineEdit()
        self.likes_edit.setPlaceholderText("oro, manzanas, poesía, magia...")
        self.likes_edit.textChanged.connect(self.on_likes_changed)
        motivations_layout.addRow("Likes (separados por comas):", self.likes_edit)

        self.dislikes_edit = QLineEdit()
        self.dislikes_edit.setPlaceholderText("ladrones, mentiras, oscuridad, goblins...")
        self.dislikes_edit.textChanged.connect(self.on_dislikes_changed)
        motivations_layout.addRow("Dislikes (separados por comas):", self.dislikes_edit)

        self.tab_widget.addTab(self.tab_motivations, "Motivaciones")

    def set_npc(self, npc: Optional[NPC]):
        self.npc = npc

        # Poblar combo de lugares con emojis
        try:
            self.initial_location_combo.currentTextChanged.disconnect(self.on_initial_location_changed)
        except Exception:
            pass

        self.initial_location_combo.clear()
        self.initial_location_combo.addItem("(Ninguno / Aparece por evento o LoreBlock)", None)

        controller = self.controller or getattr(self.parent_app, "controller", None)
        all_places = controller.get_all_places() if controller else []
        for p in all_places:
            self.initial_location_combo.addItem(f"📍 {p.name} ({p.id})", p.id)

        if not npc:
            self.id_label.setText("-")
            self.name_edit.clear()
            self.desc_edit.clear()
            self.state_edit.clear()
            self.affinity_spin.setValue(0.5)
            self.likes_edit.clear()
            self.dislikes_edit.clear()
            return

        self.id_label.setText(f"👤 {npc.id}")
        self.name_edit.setText(npc.name)
        self.desc_edit.setPlainText(npc.description or "")
        self.state_edit.setText(npc.state or "idle")
        self.affinity_spin.setValue(npc.affinity)

        # Seleccionar ubicación inicial
        current_init = npc.initial_location
        idx = 0
        if current_init:
            for i in range(1, self.initial_location_combo.count()):
                pid = self.initial_location_combo.itemData(i)
                if pid == current_init or current_init in self.initial_location_combo.itemText(i):
                    idx = i
                    break
        self.initial_location_combo.setCurrentIndex(idx)

        # Motivaciones
        if npc.motivations:
            self.likes_edit.setText(", ".join(npc.motivations.likes))
            self.dislikes_edit.setText(", ".join(npc.motivations.dislikes))
        else:
            self.likes_edit.clear()
            self.dislikes_edit.clear()

        self.initial_location_combo.currentTextChanged.connect(self.on_initial_location_changed)

    def on_name_changed(self, text: str):
        if self.npc:
            self.npc.name = text

    def on_desc_changed(self):
        if self.npc:
            self.npc.description = self.desc_edit.toPlainText()

    def on_initial_location_changed(self, _text: str):
        if self.npc:
            selected_pid = self.initial_location_combo.currentData()
            self.npc.initial_location = selected_pid

    def on_state_changed(self, text: str):
        if self.npc:
            self.npc.state = text

    def on_affinity_changed(self, val: float):
        if self.npc:
            self.npc.affinity = val

    def on_likes_changed(self, text: str):
        if self.npc and self.npc.motivations:
            self.npc.motivations.likes = [item.strip() for item in text.split(",") if item.strip()]

    def on_dislikes_changed(self, text: str):
        if self.npc and self.npc.motivations:
            self.npc.motivations.dislikes = [item.strip() for item in text.split(",") if item.strip()]


    def on_delete_clicked(self):
        if self.npc and self.parent_app and hasattr(self.parent_app, "delete_npc"):
            self.parent_app.delete_npc(self.npc)
