from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QTextEdit, QLabel, QDoubleSpinBox, QTabWidget, QVBoxLayout
from domains import NPC

class NPCForm(QWidget):
    """
    Formulario para editar las propiedades de un Personaje no Jugador (NPC).
    Organizado en pestañas para mayor orden.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.npc: NPC = None

        # Layout Principal: Contiene el widget de pestañas
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Pestaña 1: Datos Generales
        self.tab_general = QWidget()
        general_layout = QFormLayout(self.tab_general)
        
        self.id_label = QLabel()
        general_layout.addRow("ID del NPC:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        general_layout.addRow("Nombre del NPC:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        general_layout.addRow("Descripción del NPC:", self.desc_edit)

        self.state_edit = QLineEdit()
        self.state_edit.textChanged.connect(self.on_state_changed)
        general_layout.addRow("Estado del NPC (State):", self.state_edit)

        self.affinity_spin = QDoubleSpinBox()
        self.affinity_spin.setRange(0.0, 1.0)
        self.affinity_spin.setSingleStep(0.1)
        self.affinity_spin.valueChanged.connect(self.on_affinity_changed)
        general_layout.addRow("Afinidad Inicial (0.0 a 1.0):", self.affinity_spin)

        self.tab_widget.addTab(self.tab_general, "Datos Generales")

        # Pestaña 2: Motivaciones
        self.tab_motivations = QWidget()
        motivations_layout = QFormLayout(self.tab_motivations)

        self.likes_edit = QLineEdit()
        self.likes_edit.textChanged.connect(self.on_likes_changed)
        motivations_layout.addRow("Likes (separados por coma):", self.likes_edit)

        self.dislikes_edit = QLineEdit()
        self.dislikes_edit.textChanged.connect(self.on_dislikes_changed)
        motivations_layout.addRow("Dislikes (separados por coma):", self.dislikes_edit)

        self.tab_widget.addTab(self.tab_motivations, "Motivaciones")

        # Pestaña 3: Lore Dinámico y Diálogo
        from editor.views.lore_widget import LoreBlockTableWidget
        self.lore_widget = LoreBlockTableWidget()
        self.lore_widget.lore_changed.connect(self.on_lore_changed)
        self.tab_widget.addTab(self.lore_widget, "Lore y Diálogo")

    def set_npc(self, npc: NPC):
        self.npc = npc
        if npc:
            self.id_label.setText(npc.id)
            self.name_edit.setText(npc.name)
            self.desc_edit.setPlainText(npc.description)
            self.state_edit.setText(npc.state)
            self.affinity_spin.setValue(npc.affinity)
            
            # Motivaciones
            if npc.motivations:
                self.likes_edit.setText(", ".join(npc.motivations.likes))
                self.dislikes_edit.setText(", ".join(npc.motivations.dislikes))
            else:
                self.likes_edit.clear()
                self.dislikes_edit.clear()

            # Lore Dinámico
            self.lore_widget.set_lore_blocks(npc.dynamic_lore)

    def on_lore_changed(self):
        if self.npc:
            self.npc.dynamic_lore = self.lore_widget.get_lore_blocks()

    def on_name_changed(self, text: str):
        if self.npc:
            self.npc.name = text

    def on_desc_changed(self):
        if self.npc:
            self.npc.description = self.desc_edit.toPlainText()

    def on_state_changed(self, text: str):
        if self.npc:
            self.npc.state = text

    def on_affinity_changed(self, val: float):
        if self.npc:
            self.npc.affinity = val

    def on_likes_changed(self, text: str):
        if self.npc and self.npc.motivations:
            self.npc.motivations.likes = [item.strip() for item in text.split(",") if item.strip()]

    def on_dislikes_changed(self, text: str):
        if self.npc and self.npc.motivations:
            self.npc.motivations.dislikes = [item.strip() for item in text.split(",") if item.strip()]
