from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QPushButton
)
from domains import Location


class LocationForm(QWidget):
    """
    Formulario para editar las propiedades de una Localización (Location).
    Incluye botón para eliminar la localización actual.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.location: Location = None
        self.parent_app = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Barra superior con título y botón de eliminar
        top_bar = QHBoxLayout()
        self.title_label = QLabel("<b>🗺️ Localización</b>")
        self.title_label.setStyleSheet("font-size: 14px; color: #333;")
        top_bar.addWidget(self.title_label)

        top_bar.addStretch()

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.setToolTip("Eliminar esta localización y sus lugares")
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

        # Formulario
        form_layout = QFormLayout()
        
        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold; color: #555;")
        form_layout.addRow("ID de la Localización:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        form_layout.addRow("Nombre de la Localización:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        form_layout.addRow("Descripción:", self.desc_edit)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

    def set_location(self, location: Location):
        self.location = location
        if location:
            self.id_label.setText(f"🗺️ {location.id}")
            self.name_edit.setText(location.name)
            self.desc_edit.setPlainText(location.description or "")
        else:
            self.id_label.setText("-")
            self.name_edit.clear()
            self.desc_edit.clear()

    def on_name_changed(self, text: str):
        if self.location:
            self.location.name = text

    def on_desc_changed(self):
        if self.location:
            self.location.description = self.desc_edit.toPlainText()

    def on_delete_clicked(self):
        if self.location and self.parent_app and hasattr(self.parent_app, "delete_location"):
            self.parent_app.delete_location(self.location)
