from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QTextEdit, QLabel

from domains import World


class WorldForm(QWidget):
    """
    Formulario para editar las propiedades del Mundo (World).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.world: World = None

        layout = QFormLayout(self)

        self.id_label = QLabel()
        layout.addRow("ID del Mundo:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        layout.addRow("Nombre del Mundo:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        layout.addRow("Descripción del Mundo:", self.desc_edit)

        self.initial_text_edit = QTextEdit()
        self.initial_text_edit.setPlaceholderText(
            "Texto que el Dungeon Master relatará al iniciar la partida (Turno 0)...")
        self.initial_text_edit.setMaximumHeight(80)
        self.initial_text_edit.textChanged.connect(self.on_initial_text_changed)
        layout.addRow("Texto Inicial (Dungeon Master):", self.initial_text_edit)

    def set_world(self, world: World):
        self.world = world
        if world:
            self.id_label.setText(world.id)
            self.name_edit.setText(world.name)
            self.desc_edit.setPlainText(world.description)
            self.initial_text_edit.setPlainText(getattr(world, "initial_text", "") or "")

    def on_name_changed(self, text: str):
        if self.world:
            self.world.name = text

    def on_desc_changed(self):
        if self.world:
            self.world.description = self.desc_edit.toPlainText()

    def on_initial_text_changed(self):
        if self.world:
            self.world.initial_text = self.initial_text_edit.toPlainText().strip()
