from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
)
from typing import List, Optional
from domains import Place

class ConnectionDialog(QDialog):
    """
    Diálogo para crear una nueva conexión bidireccional entre lugares.
    Sugerirá automáticamente la dirección opuesta correspondiente.
    """

    OPPOSITES = {
        "North": "South",
        "South": "North",
        "East": "West",
        "West": "East"
    }

    def __init__(self, origin_place: Place, other_places: List[Place], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir Conexión Bidireccional")
        self.origin_place = origin_place
        self.other_places = other_places

        layout = QFormLayout(self)

        # 1. Origen (Lectura)
        layout.addRow("Lugar Origen:", QLabel(f"<b>{origin_place.name}</b>"))

        # 2. Destino
        self.dest_combo = QComboBox()
        for p in other_places:
            if p.id != origin_place.id:
                self.dest_combo.addItem(p.name, p.name)
        layout.addRow("Lugar Destino:", self.dest_combo)

        # 3. Dirección (Origen -> Destino)
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["North", "South", "East", "West"])
        layout.addRow("Dirección (Origen -> Destino):", self.dir_combo)

        # 4. Dirección Opuesta (Destino -> Origen)
        self.opp_dir_combo = QComboBox()
        self.opp_dir_combo.addItems(["North", "South", "East", "West"])
        layout.addRow("Dirección Opuesta (Destino -> Origen):", self.opp_dir_combo)

        # 5. Distancia (Metros)
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 100000)
        self.distance_spin.setValue(100)
        self.distance_spin.setSuffix(" metros")
        layout.addRow("Distancia:", self.distance_spin)

        # 6. Terreno
        self.terrain_combo = QComboBox()
        self.terrain_combo.addItems(["village", "road", "forest", "mountain", "swamp"])
        layout.addRow("Tipo de Terreno:", self.terrain_combo)

        # 7. Permitir Paso / Conexión abierta
        self.passable_check = QCheckBox("Permitir paso (Conexión abierta)")
        self.passable_check.setChecked(True)
        layout.addRow("Estado del Paso:", self.passable_check)

        # 8. Botones Aceptar / Cancelar
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        # Señal para auto-sugerir dirección opuesta
        self.dir_combo.currentTextChanged.connect(self.on_direction_changed)
        self.on_direction_changed(self.dir_combo.currentText())

    def on_direction_changed(self, text: str):
        opposite = self.OPPOSITES.get(text, "North")
        self.opp_dir_combo.setCurrentText(opposite)

    def get_data(self):
        """
        Retorna la tupla con los datos de conexión:
        (lugar_destino_name, dir_ab, dir_ba, distancia, terreno, passable)
        """
        dest_name = self.dest_combo.currentData()
        return (
            dest_name or "",
            self.dir_combo.currentText(),
            self.opp_dir_combo.currentText(),
            self.distance_spin.value(),
            self.terrain_combo.currentText(),
            self.passable_check.isChecked()
        )

