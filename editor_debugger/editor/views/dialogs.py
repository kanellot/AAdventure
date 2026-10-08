from typing import List, Optional, Tuple

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

from domains import Place
from editor_debugger.editor.constants import TYPE_METADATA, get_allowed_child_types


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
    Diálogo modal para crear un nuevo LoreBlock con filtrado dinámico
    estricto según la matriz de jerarquía HSM y metadatos de iconos.
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
        self.resize(480, 230)

        self.all_blocks = all_blocks or []
        self.blocks_by_id = {b.id: b for b in self.all_blocks}
        self.default_target_type = default_type

        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título o nombre del bloque...")
        layout.addRow("Título / Nombre:", self.title_edit)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("(Ninguno - Bloque Raíz)", "")
        for b in self.all_blocks:
            b_title = getattr(b, "title", "") or getattr(b, "name", "") or b.id
            b_type = getattr(b, "type", "Event")
            icon = TYPE_METADATA.get(b_type, {}).get("icon", "📁")
            self.parent_combo.addItem(f"{icon} {b_title} ({b.id})", b.id)

        layout.addRow("Bloque Padre (HSM):", self.parent_combo)

        self.type_combo = QComboBox()
        layout.addRow("Tipo de Bloque:", self.type_combo)

        # Conectar cambio de padre a actualización dinámica de tipos permitidos
        self.parent_combo.currentIndexChanged.connect(self.on_parent_changed)

        if parent_id:
            pidx = self.parent_combo.findData(parent_id)
            if pidx >= 0:
                self.parent_combo.setCurrentIndex(pidx)
            else:
                self.parent_combo.addItem(f"📁 {parent_id}", parent_id)
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
        else:
            self.parent_combo.setCurrentIndex(0)

        self.on_parent_changed()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Crear")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def on_parent_changed(self):
        """Filtra los tipos permitidos según la regla estricta de anidamiento."""
        pid = self.parent_combo.currentData()
        parent_block = self.blocks_by_id.get(pid) if pid else None
        parent_type = getattr(parent_block, "type", None) if parent_block else None

        allowed = get_allowed_child_types(parent_type)

        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for t in allowed:
            meta = TYPE_METADATA.get(t, {"icon": "📜", "label": t})
            self.type_combo.addItem(f"{meta['icon']} {meta['label']}", t)

        idx = self.type_combo.findData(self.default_target_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        else:
            self.type_combo.setCurrentIndex(0)
        self.type_combo.blockSignals(False)

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
