from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QComboBox
from typing import List
from domains import Player, Place

class PlayerForm(QWidget):
    """
    Formulario para editar las propiedades del Jugador (Player) y su estado inicial.
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

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 100.0)
        self.speed_spin.setSingleStep(0.5)
        self.speed_spin.setSuffix(" km/h")
        self.speed_spin.valueChanged.connect(self.on_speed_changed)
        layout.addRow("Velocidad de Viaje base:", self.speed_spin)

        self.loc_combo = QComboBox()
        self.loc_combo.currentTextChanged.connect(self.on_loc_changed)
        layout.addRow("Lugar Inicial del Jugador:", self.loc_combo)

    def set_player(self, player: Player, all_places: List[Place]):
        self.player = player
        
        # Guardar señal temporalmente desconectada para evitar ciclos de eventos al poblar
        self.loc_combo.currentTextChanged.disconnect(self.on_loc_changed)
        self.loc_combo.clear()
        
        # Rellenar lista de lugares
        place_names = [p.name for p in all_places]
        for name in place_names:
            self.loc_combo.addItem(name)
        
        if player:
            self.id_label.setText(player.id)
            self.name_edit.setText(player.name)
            self.desc_edit.setPlainText(player.description)
            self.gold_spin.setValue(player.gold)
            self.speed_spin.setValue(player.travel_speed)
            
            # Salvaguarda: si está vacío o no es un lugar existente, se asigna el primero disponible
            if (not player.player_location or player.player_location not in place_names) and place_names:
                player.player_location = place_names[0]
                
            self.loc_combo.setCurrentText(player.player_location)
            
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

    def on_speed_changed(self, val: float):
        if self.player:
            self.player.travel_speed = val

    def on_loc_changed(self, text: str):
        if self.player:
            self.player.player_location = text
