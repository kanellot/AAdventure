from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
)
from typing import List, Optional, Tuple
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

        # 7. Botones Aceptar / Cancelar
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
        (lugar_destino_name, dir_ab, dir_ba, distancia, terreno)
        """
        dest_name = self.dest_combo.currentData()
        return (
            dest_name or "",
            self.dir_combo.currentText(),
            self.opp_dir_combo.currentText(),
            self.distance_spin.value(),
            self.terrain_combo.currentText()
        )


class CreateLoreBlockDialog(QDialog):
    """
    Diálogo modal para crear un nuevo LoreBlock permitiendo seleccionar
    su título, tipo canónico (Chapter, Quest, Task, Event, popup_event -> "popup")
    y bloque padre opcional.
    """

    def __init__(
        self,
        default_type: str = "Event",
        parent_id: Optional[str] = None,
        all_blocks: Optional[List] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Crear Bloque de Lore")
        self.resize(460, 220)

        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título o nombre del bloque...")
        layout.addRow("Título / Nombre:", self.title_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItem("📖 Chapter (Capítulo - Contenedor)", "Chapter")
        self.type_combo.addItem("⚔️ Quest (Misión Principal)", "Quest")
        self.type_combo.addItem("📌 Task (Tarea / Objetivo)", "Task")
        self.type_combo.addItem("⚡ Event (Evento sobre Entidades)", "Event")
        self.type_combo.addItem("📢 Pop-up Event (popup_event)", "popup")

        target_type = "popup" if default_type in ("popup", "popup_event", "event_popup") else default_type
        idx = self.type_combo.findData(target_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        layout.addRow("Tipo de Bloque:", self.type_combo)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")
        if all_blocks:
            for b in all_blocks:
                b_title = getattr(b, "title", "") or getattr(b, "name", "") or b.id
                self.parent_combo.addItem(f"📁 {b_title} ({b.id})", b.id)

        if parent_id:
            pidx = self.parent_combo.findData(parent_id)
            if pidx >= 0:
                self.parent_combo.setCurrentIndex(pidx)
            else:
                self.parent_combo.addItem(f"📁 {parent_id}", parent_id)
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
        layout.addRow("Bloque Padre (HSM):", self.parent_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Crear")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def on_accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validación", "Debes ingresar un título o nombre para el bloque.")
            return
        self.accept()

    def get_data(self) -> Tuple[str, str, Optional[str]]:
        """Retorna la tupla: (title, type, parent_id)."""
        p_val = self.parent_combo.currentData()
        return (
            self.title_edit.text().strip(),
            self.type_combo.currentData() or "Event",
            p_val if p_val else None,
        )


