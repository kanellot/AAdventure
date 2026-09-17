"""Widgets visuales y árbol jerárquico para la gestión de LoreBlocks (HSM)."""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from domains.lore import LoreBlock, LoreBlockState
from editor.views.lore_block_form import LoreBlockForm


class LoreBlockEditorDialog(QDialog):
    """Diálogo modal que contiene LoreBlockForm para crear o editar un LoreBlock completo."""

    def __init__(
        self,
        lore_block: Optional[LoreBlock] = None,
        controller=None,
        initial_parent_id: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configurar LoreBlock (HSM)")
        self.resize(800, 700)
        self.controller = controller

        if lore_block is None:
            new_id = (
                f"lb_{len(controller.lore_blocks) + 1:02d}"
                if controller and hasattr(controller, "lore_blocks")
                else "lb_new"
            )
            self.block = LoreBlock(id=new_id, title="", parent_id=initial_parent_id)
        else:
            self.block = lore_block.model_copy(deep=True)

        layout = QVBoxLayout(self)
        self.form = LoreBlockForm(controller=controller, parent=self)
        if hasattr(self.form, "del_btn"):
            self.form.del_btn.setVisible(False)
        self.form.set_lore_block(self.block)
        layout.addWidget(self.form)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_accept(self):
        if not self.block.id.strip():
            QMessageBox.warning(self, "Validación", "El identificador del bloque no puede estar vacío.")
            return
        self.accept()

    def get_data(self) -> LoreBlock:
        return self.block


class LoreBlockTreeWidget(QWidget):
    """Widget de explorador jerárquico tipo árbol (HSM / Carpetas de Archivos) para gestionar LoreBlocks."""

    lore_changed = Signal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.lore_blocks: List[LoreBlock] = []

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels([
            "Jerarquía de LoreBlocks (Carpetas / Archivos)",
            "Afecta a (Entidades)",
            "Estado HSM",
            "Modo",
            "Condiciones / Salida",
            "RAG",
        ])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tree.itemDoubleClicked.connect(self.on_edit_block)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.add_root_btn = QPushButton("➕ Añadir Bloque Raíz...")
        self.add_root_btn.clicked.connect(self.on_add_root_block)

        self.add_child_btn = QPushButton("📁➕ Añadir Sub-bloque...")
        self.add_child_btn.clicked.connect(self.on_add_child_block)

        self.edit_btn = QPushButton("✏️ Editar...")
        self.edit_btn.clicked.connect(self.on_edit_block)

        self.del_btn = QPushButton("🗑️ Eliminar")
        self.del_btn.clicked.connect(self.on_delete_block)

        btn_layout.addWidget(self.add_root_btn)
        btn_layout.addWidget(self.add_child_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)

    def set_controller(self, controller):
        self.controller = controller

    def set_lore_blocks(self, lore_blocks: List[LoreBlock]):
        self.lore_blocks = lore_blocks or []
        self.populate_tree()

    def get_lore_blocks(self) -> List[LoreBlock]:
        return self.lore_blocks

    def populate_tree(self):
        self.tree.clear()
        if not self.lore_blocks:
            return

        id_to_block = {b.id: b for b in self.lore_blocks}
        parent_to_children = {}
        for b in self.lore_blocks:
            p_id = getattr(b, "parent_id", None)
            if p_id and p_id in id_to_block:
                parent_to_children.setdefault(p_id, []).append(b)

        roots = [b for b in self.lore_blocks if not b.parent_id or b.parent_id not in id_to_block]

        def create_tree_item(parent_widget, block: LoreBlock):
            item = QTreeWidgetItem(parent_widget)
            item.setData(0, Qt.UserRole, block.id)

            has_children = block.id in parent_to_children and bool(parent_to_children[block.id])

            if has_children:
                icon_prefix = "📂 " if block.state == LoreBlockState.ACTIVE or str(block.state).lower() == "active" else "📁 "
            else:
                icon_prefix = "📜 "

            title = block.title or (block.directive[:35] + "..." if len(block.directive) > 35 else block.directive)
            item.setText(0, f"{icon_prefix}{title}  ({block.id})")

            # Columna 1: Afecta a
            targets = [eff.target for eff in block.effects if eff.target]
            item.setText(1, ", ".join(targets) if targets else "(Ninguna)")

            # Columna 2: Estado HSM
            st = block.state.value.upper() if hasattr(block.state, "value") else str(block.state).upper()
            if st == "ACTIVE":
                item.setText(2, "🟢 ACTIVO (Abierto)")
                item.setForeground(2, Qt.darkGreen)
            elif st == "DONE":
                item.setText(2, "🔵 RESUELTO")
                item.setForeground(2, Qt.blue)
            elif st == "INACTIVE":
                item.setText(2, "⚪ INACTIVO")
                item.setForeground(2, Qt.darkGray)
            else:
                item.setText(2, f"⚪ {st}")
                item.setForeground(2, Qt.darkGray)

            # Columna 3: Modo
            item.setText(3, block.trigger_mode.capitalize())

            # Columna 4: Condiciones
            c_info = f"{len(block.conditions)} act."
            if block.exit_conditions:
                c_info += f" / {len(block.exit_conditions)} sal."
            item.setText(4, c_info)

            # Columna 5: RAG
            item.setText(5, "Sí" if block.rag_enabled else "No")

            for child in parent_to_children.get(block.id, []):
                create_tree_item(item, child)

            return item

        for r in roots:
            create_tree_item(self.tree, r)

        self.tree.expandAll()

    def get_selected_block(self) -> Optional[LoreBlock]:
        item = self.tree.currentItem()
        if not item:
            return None
        b_id = item.data(0, Qt.UserRole)
        for b in self.lore_blocks:
            if b.id == b_id:
                return b
        return None

    def on_add_root_block(self):
        dialog = LoreBlockEditorDialog(controller=self.controller, initial_parent_id=None, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_block = dialog.get_data()
            self.lore_blocks.append(new_block)
            self.populate_tree()
            self.lore_changed.emit()

    def on_add_child_block(self):
        selected = self.get_selected_block()
        parent_id = selected.id if selected else None
        dialog = LoreBlockEditorDialog(controller=self.controller, initial_parent_id=parent_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_block = dialog.get_data()
            self.lore_blocks.append(new_block)
            self.populate_tree()
            self.lore_changed.emit()

    def on_edit_block(self):
        selected = self.get_selected_block()
        if not selected:
            QMessageBox.information(self, "Selección", "Por favor, selecciona un bloque en el árbol para editar.")
            return

        dialog = LoreBlockEditorDialog(lore_block=selected, controller=self.controller, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_block = dialog.get_data()
            idx = next((i for i, b in enumerate(self.lore_blocks) if b.id == selected.id), -1)
            if idx >= 0:
                self.lore_blocks[idx] = updated_block
            self.populate_tree()
            self.lore_changed.emit()

    def on_delete_block(self):
        selected = self.get_selected_block()
        if not selected:
            QMessageBox.information(self, "Selección", "Por favor, selecciona un bloque para eliminar.")
            return

        children = [b for b in self.lore_blocks if getattr(b, "parent_id", None) == selected.id]
        if children:
            res = QMessageBox.question(
                self, "Eliminar LoreBlock Contenedor",
                f"El bloque '{selected.id}' contiene {len(children)} sub-bloque(s).\n\n"
                "¿Deseas eliminarlo JUNTO con todos sus sub-bloques en cascada?\n\n"
                "(Si eliges 'No', los sub-bloques se promoverán al nivel superior/raíz)",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if res == QMessageBox.Cancel:
                return
            elif res == QMessageBox.Yes:
                ids_to_del = {selected.id}
                changed = True
                while changed:
                    changed = False
                    for b in self.lore_blocks:
                        if b.id not in ids_to_del and getattr(b, "parent_id", None) in ids_to_del:
                            ids_to_del.add(b.id)
                            changed = True
                self.lore_blocks = [b for b in self.lore_blocks if b.id not in ids_to_del]
            else:
                for c in children:
                    c.parent_id = selected.parent_id
                self.lore_blocks = [b for b in self.lore_blocks if b.id != selected.id]
        else:
            confirm = QMessageBox.question(
                self, "Eliminar Lore",
                f"¿Estás seguro de eliminar el bloque '{selected.id}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            self.lore_blocks = [b for b in self.lore_blocks if b.id != selected.id]

        self.populate_tree()
        self.lore_changed.emit()
