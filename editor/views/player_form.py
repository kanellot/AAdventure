from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QLabel,
    QSpinBox,
    QComboBox,
)
from typing import List
from domains import Player, Place, LoreBlock


class PlayerForm(QWidget):
    """
    Formulario para editar las propiedades del Jugador (Player) y su estado inicial.
    Exige obligatoriamente la asignación a un lugar de inicio (initial_place).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player: Player = None

        layout = QFormLayout(self)

        self.id_label = QLabel()
        layout.addRow("ID del Jugador:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        layout.addRow("Nombre del Personaje:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        layout.addRow("Descripción del Personaje:", self.desc_edit)

        self.gold_spin = QSpinBox()
        self.gold_spin.setRange(0, 1000000)
        self.gold_spin.valueChanged.connect(self.on_gold_changed)
        layout.addRow("Oro Inicial:", self.gold_spin)

        self.inventory_edit = QLineEdit()
        self.inventory_edit.setPlaceholderText("IDs de objetos separados por comas (ej. obj_daga, obj_pocion)")
        self.inventory_edit.textChanged.connect(self.on_inventory_changed)
        layout.addRow("Inventario Inicial:", self.inventory_edit)

        self.active_block_edit = QLineEdit()
        self.active_block_edit.setPlaceholderText("ID del LoreBlock activo inicial (ej. lb_prologo)")
        self.active_block_edit.textChanged.connect(self.on_active_block_changed)
        layout.addRow("LoreBlock Activo Inicial:", self.active_block_edit)

        self.loc_combo = QComboBox()
        self.loc_combo.currentTextChanged.connect(self.on_loc_changed)
        layout.addRow("Lugar Inicial (*OBLIGATORIO*):", self.loc_combo)

    def set_player(self, player: Player, all_places: List[Place]):
        self.player = player

        # Desconectar señal temporalmente para poblar
        try:
            self.loc_combo.currentTextChanged.disconnect(self.on_loc_changed)
        except Exception:
            pass

        self.loc_combo.clear()

        # Poblar lista de lugares con ID y Nombre
        for p in all_places:
            self.loc_combo.addItem(f"{p.name} ({p.id})", p.id)

        if player:
            self.id_label.setText(player.id)
            self.name_edit.setText(player.name)
            self.desc_edit.setPlainText(player.description or "")
            self.gold_spin.setValue(player.gold)
            self.inventory_edit.setText(", ".join(player.inventory or []))
            self.active_block_edit.setText(player.active_block or "")

            current_init = player.initial_place or player.player_location or ""
            idx = -1
            for i in range(self.loc_combo.count()):
                pid = self.loc_combo.itemData(i)
                text = self.loc_combo.itemText(i)
                if pid == current_init or current_init in text:
                    idx = i
                    break

            if idx >= 0:
                self.loc_combo.setCurrentIndex(idx)
            elif self.loc_combo.count() > 0:
                self.loc_combo.setCurrentIndex(0)
                first_pid = self.loc_combo.itemData(0)
                player.initial_place = first_pid
                player.player_location = first_pid

        self.loc_combo.currentTextChanged.connect(self.on_loc_changed)

    def on_name_changed(self, text: str):
        if self.player:
            self.player.name = text

    def on_desc_changed(self):
        if self.player:
            self.player.description = self.desc_edit.toPlainText()

    def on_gold_changed(self, val: int):
        if self.player:
            self.player.gold = val

    def on_inventory_changed(self, text: str):
        if self.player:
            items = [item.strip() for item in text.split(",") if item.strip()]
            self.player.inventory = items

    def on_active_block_changed(self, text: str):
        if self.player:
            self.player.active_block = text.strip() if text.strip() else None

    def on_loc_changed(self, _text: str):
        if self.player:
            pid = self.loc_combo.currentData()
            if pid:
                self.player.initial_place = pid
                self.player.player_location = pid
