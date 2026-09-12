from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QTextEdit, QLabel
from domains import Location

class LocationForm(QWidget):
    """
    Formulario para editar las propiedades de una Localización (Location).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.location: Location = None

        layout = QFormLayout(self)
        
        self.id_label = QLabel()
        layout.addRow("ID de la Localización:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        layout.addRow("Nombre de la Localización:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        layout.addRow("Descripción:", self.desc_edit)

    def set_location(self, location: Location):
        self.location = location
        if location:
            self.id_label.setText(location.id)
            self.name_edit.setText(location.name)
            self.desc_edit.setPlainText(location.description)

    def on_name_changed(self, text: str):
        if self.location:
            self.location.name = text

    def on_desc_changed(self):
        if self.location:
            self.location.description = self.desc_edit.toPlainText()
