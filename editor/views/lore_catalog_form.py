"""Vista para gestionar el catálogo centralizado de LoreBlocks (HSM) de la historia."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from typing import List
from domains.lore import LoreBlock
from editor.views.lore_widget import LoreBlockTreeWidget


class LoreCatalogForm(QWidget):
    """Vista de catálogo global de LoreBlocks en el editor."""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)

        group = QGroupBox("Catálogo Centralizado de Bloques de Lore (Máquina de Estados HSM)")
        group_layout = QVBoxLayout(group)

        desc = QLabel(
            "Aquí se definen todos los bloques narrativos de la aventura organizados jerárquicamente como carpetas y archivos (HSM). "
            "Un bloque activo actúa como una carpeta abierta que contiene sub-bloques evaluables hasta que se cumple la condición de salida del padre."
        )
        desc.setWordWrap(True)
        group_layout.addWidget(desc)

        self.tree_widget = LoreBlockTreeWidget(controller=controller)
        self.tree_widget.lore_changed.connect(self.on_lore_changed)
        group_layout.addWidget(self.tree_widget)

        layout.addWidget(group)

    def set_lore_blocks(self, blocks: List[LoreBlock]):
        self.tree_widget.set_lore_blocks(blocks)

    def get_lore_blocks(self) -> List[LoreBlock]:
        return self.tree_widget.get_lore_blocks()

    def on_lore_changed(self):
        if self.controller:
            self.controller.lore_blocks = self.tree_widget.get_lore_blocks()
