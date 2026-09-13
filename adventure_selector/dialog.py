"""Diálogo modal PySide6 para la selección de aventuras (.aad)."""

import os
from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QCheckBox,
    QFileDialog,
    QFrame,
    QMessageBox,
)
from PySide6.QtGui import QFont

from adventure_selector.models import AdventureMetadata
from adventure_selector.reader import read_adventure_metadata
from adventure_selector.scanner import scan_adventures
from adventure_selector.storage import (
    get_default_adventure_path,
    set_default_adventure_path,
)

SEPIA_DIALOG_STYLESHEET = """
QDialog {
    background-color: #f3ebc6;
    color: #3e2b14;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QLineEdit {
    background-color: #faf6df;
    color: #3e2b14;
    border: 1px solid #d5c796;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1.5px solid #b58238;
}

QListWidget {
    background-color: #faf6df;
    border: 1px solid #d5c796;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    border-radius: 6px;
    margin-bottom: 6px;
}

QListWidget::item:hover {
    background-color: #f5eed1;
}

QListWidget::item:selected {
    background-color: #eee4ba;
    border: 1.5px solid #b58238;
}

QPushButton {
    background-color: #e6dca8;
    color: #3e2b14;
    border: 1px solid #d5c796;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #decfa0;
}

QPushButton:pressed {
    background-color: #d1c18d;
}

QPushButton:disabled {
    background-color: #e0d9bd;
    color: #9c8e76;
    border-color: #c7bda0;
}

QCheckBox {
    color: #3e2b14;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #b58238;
    border-radius: 3px;
    background: #faf6df;
}

QCheckBox::indicator:checked {
    background-color: #b58238;
}
"""


class AdventureCardWidget(QWidget):
    """Widget de ficha visual enriquecida para una aventura."""

    def __init__(self, meta: AdventureMetadata, is_default: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.meta = meta

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Fila 1: Título, distintivo por defecto y metadatos del archivo
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title_text = f"🗺️ {meta.title}" if meta.is_valid else f"⚠️ {meta.file_name}"
        title_label = QLabel(title_text)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #3e2b14;")
        header_layout.addWidget(title_label)

        if is_default:
            default_badge = QLabel("⭐ Por defecto")
            default_badge.setStyleSheet(
                "background-color: #dfce8f; color: #4a340b; border: 1px solid #b58238; "
                "border-radius: 3px; padding: 2px 6px; font-weight: bold; font-size: 11px;"
            )
            header_layout.addWidget(default_badge)

        header_layout.addStretch()

        file_meta_label = QLabel(f"{meta.file_name}  •  {meta.file_size_kb} KB  •  {meta.modified_time}")
        file_meta_label.setStyleSheet("color: #7a664d; font-size: 11px;")
        header_layout.addWidget(file_meta_label)
        layout.addLayout(header_layout)

        # Fila 2: Descripción (si es válida)
        if meta.is_valid and meta.description:
            desc_text = meta.description.strip()
            if len(desc_text) > 140:
                desc_text = desc_text[:137] + "..."
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet("color: #5c401f; font-style: italic; font-size: 12px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Fila 3: Jugador y lugar de inicio
        if meta.is_valid:
            player_line = QLabel(
                f"👤 <b>{meta.player_name}</b>  |  📍 Inicio: <b>{meta.initial_place or 'Sin definir'}</b>"
            )
            player_line.setStyleSheet("color: #4a3820; font-size: 12px;")
            layout.addWidget(player_line)

        # Fila 4: Badges con métricas de entidades
        if meta.is_valid:
            metrics_layout = QHBoxLayout()
            metrics_layout.setSpacing(6)

            chips = [
                f"📍 {meta.places_count} Lugares",
                f"👤 {meta.npcs_count} NPCs",
                f"📦 {meta.objects_count} Objetos",
                f"📜 {meta.lore_blocks_count} LoreBlocks",
            ]
            for chip_text in chips:
                chip = QLabel(chip_text)
                chip.setStyleSheet(
                    "background-color: #eae0b2; color: #3e2b14; border: 1px solid #cfbe8c; "
                    "border-radius: 4px; padding: 2px 7px; font-size: 11px;"
                )
                metrics_layout.addWidget(chip)

            metrics_layout.addStretch()
            layout.addLayout(metrics_layout)
        else:
            err_label = QLabel(f"Error: {meta.error_message or 'Archivo ilegible'}")
            err_label.setStyleSheet("color: #a02020; font-size: 11px; font-weight: bold;")
            layout.addWidget(err_label)


class AdventureSelectorDialog(QDialog):
    """Diálogo modal para listar, filtrar y seleccionar una aventura .aad."""

    adventure_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, preselected_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Aventura - AAdventure")
        self.resize(760, 560)
        self.setModal(True)
        self.setStyleSheet(SEPIA_DIALOG_STYLESHEET)

        self.adventures: List[AdventureMetadata] = []
        self.default_path = get_default_adventure_path()
        self.selected_path: Optional[str] = preselected_path or self.default_path

        self._init_ui()
        self._load_adventures()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Encabezado
        header_layout = QHBoxLayout()
        header_label = QLabel("📜 Seleccionar Aventura de Juego")
        hfont = QFont()
        hfont.setBold(True)
        hfont.setPointSize(13)
        header_label.setFont(hfont)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Barra de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar por título, descripción, jugador o nombre de archivo...")
        self.search_input.textChanged.connect(self._apply_filter)
        main_layout.addWidget(self.search_input)

        # Lista de aventuras
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget)

        # Fila de opciones: Examinar archivo y Casilla por defecto
        options_layout = QHBoxLayout()
        self.browse_btn = QPushButton("📂 Examinar otro archivo .aad...")
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        options_layout.addWidget(self.browse_btn)

        options_layout.addStretch()

        self.set_default_check = QCheckBox("Recordar como aventura por defecto")
        self.set_default_check.setChecked(True)
        options_layout.addWidget(self.set_default_check)
        main_layout.addLayout(options_layout)

        # Separador visual
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("color: #d5c796;")
        main_layout.addWidget(sep)

        # Fila de botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        self.load_btn = QPushButton("Cargar Aventura ➔")
        self.load_btn.setStyleSheet(
            "background-color: #b58238; color: #ffffff; border: 1px solid #8e6224; "
            "border-radius: 4px; padding: 7px 18px; font-weight: bold;"
        )
        self.load_btn.clicked.connect(self._on_accept_clicked)
        buttons_layout.addWidget(self.load_btn)

        main_layout.addLayout(buttons_layout)

    def _load_adventures(self):
        """Escanea las aventuras disponibles y puebla la lista."""
        self.adventures = scan_adventures()
        self._populate_list(self.adventures)

    def _populate_list(self, items: List[AdventureMetadata]):
        self.list_widget.clear()

        norm_default = os.path.normcase(os.path.abspath(self.default_path)) if self.default_path else ""
        norm_selected = os.path.normcase(os.path.abspath(self.selected_path)) if self.selected_path else norm_default

        target_item_to_select = None

        for meta in items:
            item = QListWidgetItem(self.list_widget)
            is_def = (norm_default and os.path.normcase(os.path.abspath(meta.file_path)) == norm_default)
            card = AdventureCardWidget(meta, is_default=is_def)

            # Ajustar tamaño sugerido del item
            card_height = 100 if meta.is_valid else 75
            item.setSizeHint(QSize(0, card_height))
            self.list_widget.setItemWidget(item, card)
            item.setData(Qt.UserRole, meta.file_path)

            if norm_selected and os.path.normcase(os.path.abspath(meta.file_path)) == norm_selected:
                target_item_to_select = item

        if target_item_to_select:
            self.list_widget.setCurrentItem(target_item_to_select)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        self._on_selection_changed()

    def _apply_filter(self, text: str):
        query = text.strip().lower()
        if not query:
            filtered = self.adventures
        else:
            filtered = [
                m for m in self.adventures
                if query in m.title.lower()
                or query in m.file_name.lower()
                or query in m.description.lower()
                or query in m.player_name.lower()
                or query in m.initial_place.lower()
            ]
        self._populate_list(filtered)

    def _on_selection_changed(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            path = current_item.data(Qt.UserRole)
            self.selected_path = path
            # Buscar metadata para saber si es válida
            meta = next((m for m in self.adventures if m.file_path == path), None)
            is_valid = meta.is_valid if meta else True
            self.load_btn.setEnabled(is_valid)
        else:
            self.selected_path = None
            self.load_btn.setEnabled(False)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        if self.load_btn.isEnabled():
            self._on_accept_clicked()

    def _on_browse_clicked(self):
        """Permite examinar cualquier archivo .aad en el equipo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Aventura AAdventure",
            "",
            "Archivos de Aventura (*.aad);;Todos los Archivos (*.*)",
        )
        if not file_path:
            return

        abs_path = os.path.abspath(file_path)
        # Verificar si ya existe en la lista
        existing = next((m for m in self.adventures if os.path.normcase(m.file_path) == os.path.normcase(abs_path)), None)
        if not existing:
            meta = read_adventure_metadata(abs_path)
            self.adventures.insert(0, meta)
            self._populate_list(self.adventures)
            self.selected_path = abs_path
        else:
            self.selected_path = existing.file_path

        # Seleccionar en la lista
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and os.path.normcase(item.data(Qt.UserRole)) == os.path.normcase(self.selected_path):
                self.list_widget.setCurrentItem(item)
                break

    def _on_accept_clicked(self):
        if not self.selected_path or not os.path.exists(self.selected_path):
            QMessageBox.warning(self, "Aviso", "Por favor selecciona un archivo de aventura válido.")
            return

        if self.set_default_check.isChecked():
            set_default_adventure_path(self.selected_path)

        self.adventure_selected.emit(self.selected_path)
        self.accept()

    def get_selected_path(self) -> Optional[str]:
        return self.selected_path
