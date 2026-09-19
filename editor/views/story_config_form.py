"""Formulario para editar la configuración de simulación de historia (StoryConfig)."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QLabel, QGroupBox
from domains.story_config import StoryConfig


class StoryConfigForm(QWidget):
    """Vista de formulario para los flags de configuración de la historia."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config: StoryConfig = StoryConfig()

        main_layout = QVBoxLayout(self)

        group = QGroupBox("Opciones de Simulación y Reglas del Juego")
        form_layout = QFormLayout(group)

        self.elapsed_time_cb = QCheckBox("Activar cálculo y avance del tiempo transcurrido (Elapsed Time)")
        self.elapsed_time_cb.toggled.connect(self.on_elapsed_time_toggled)
        form_layout.addRow(self.elapsed_time_cb)

        self.fog_war_cb = QCheckBox("Activar Niebla de Guerra (Fog of War: ocultar lugares no descubiertos)")
        self.fog_war_cb.toggled.connect(self.on_fog_war_toggled)
        form_layout.addRow(self.fog_war_cb)

        self.affinity_cb = QCheckBox("Activar sistema de Afinidad con NPCs (Affinity)")
        self.affinity_cb.toggled.connect(self.on_affinity_toggled)
        form_layout.addRow(self.affinity_cb)

        main_layout.addWidget(group)
        main_layout.addStretch()

        self.set_config(self.config)

    def set_config(self, config: StoryConfig):
        self.config = config
        if config:
            self.elapsed_time_cb.setChecked(config.elapsed_time)
            self.fog_war_cb.setChecked(config.fog_war)
            self.affinity_cb.setChecked(config.affinity)

    def on_elapsed_time_toggled(self, checked: bool):
        if self.config:
            self.config.elapsed_time = checked

    def on_fog_war_toggled(self, checked: bool):
        if self.config:
            self.config.fog_war = checked

    def on_affinity_toggled(self, checked: bool):
        if self.config:
            self.config.affinity = checked
