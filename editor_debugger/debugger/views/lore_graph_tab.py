"""Pestaña de visualización de LoreBlocks (HSM) en lista de texto jerárquica con colores y símbolos."""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domains.projections import LoreBlockDetailProjection, LoreGraphProjection


class LoreGraphTab(QWidget):
    """
    Pestaña de depuración narrativa de LoreBlocks:
    Muestra una lista de texto jerárquica con sangría de padres e hijos,
    código de colores por estado (Activo, Completado, Pendiente, Bloqueado),
    símbolos visuales claros (🟢, 🔵, 🟡, 🔒, ✓, ✗) y un panel lateral de inspección detallada.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_projection: Optional[LoreGraphProjection] = None
        self.current_filter: str = "ALL"
        self.block_items: Dict[str, QTreeWidgetItem] = {}
        self.blocks_by_id: Dict[str, LoreBlockDetailProjection] = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. Barra Superior: Dividida en dos filas para evitar desbordamiento horizontal
        # Fila 1: Píldoras de métricas y botones de expandir/colapsar
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.lbl_total = QLabel("Total: 0")
        self.lbl_total.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px; background: #e0e0e0; color: #333;")

        self.lbl_active = QLabel("🟢 Activos: 0")
        self.lbl_active.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px; background: #c8e6c9; color: #1b5e20;")

        self.lbl_done = QLabel("🔵 Completados: 0")
        self.lbl_done.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px; background: #bbdefb; color: #0d47a1;")

        self.lbl_unknown = QLabel("🟡 Pendientes: 0")
        self.lbl_unknown.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px; background: #ffe0b2; color: #e65100;")

        row1.addWidget(self.lbl_total)
        row1.addWidget(self.lbl_active)
        row1.addWidget(self.lbl_done)
        row1.addWidget(self.lbl_unknown)

        row1.addStretch(1)

        self.btn_expand_all = QPushButton("Expandir")
        self.btn_expand_all.clicked.connect(self._expand_all)
        row1.addWidget(self.btn_expand_all)

        self.btn_collapse_all = QPushButton("Colapsar")
        self.btn_collapse_all.clicked.connect(self._collapse_all)
        row1.addWidget(self.btn_collapse_all)

        main_layout.addLayout(row1)

        # Fila 2: Filtros rápidos de estado y barra de búsqueda
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.btn_filter_all = QPushButton("Todos")
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setChecked(True)
        self.btn_filter_all.clicked.connect(lambda: self._set_filter("ALL"))

        self.btn_filter_active = QPushButton("Activos")
        self.btn_filter_active.setCheckable(True)
        self.btn_filter_active.clicked.connect(lambda: self._set_filter("ACTIVE"))

        self.btn_filter_done = QPushButton("Completados")
        self.btn_filter_done.setCheckable(True)
        self.btn_filter_done.clicked.connect(lambda: self._set_filter("DONE"))

        self.btn_filter_unknown = QPushButton("Pendientes")
        self.btn_filter_unknown.setCheckable(True)
        self.btn_filter_unknown.clicked.connect(lambda: self._set_filter("UNKNOWN"))

        row2.addWidget(self.btn_filter_all)
        row2.addWidget(self.btn_filter_active)
        row2.addWidget(self.btn_filter_done)
        row2.addWidget(self.btn_filter_unknown)

        row2.addSpacing(8)

        # Buscador por texto
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nombre, ID o condición...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        row2.addWidget(self.search_edit, stretch=1)

        main_layout.addLayout(row2)

        # 2. Splitter: Árbol de Texto Jerárquico (Izquierda) + Panel de Inspección de Detalle (Derecha)
        splitter = QSplitter(Qt.Horizontal)

        # Árbol de texto jerárquico
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Jerarquía de LoreBlocks (HSM) y Condiciones"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #faf6df;
                color: #2b2b2b;
                border: 1px solid #d5c796;
                border-radius: 6px;
                padding: 4px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-radius: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #d7ccc8;
                color: #3e2723;
                font-weight: bold;
            }
        """)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        splitter.addWidget(self.tree)

        # Panel de Detalle en HTML enriquecido
        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(False)
        self.detail_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                color: #2b2b2b;
                border: 1px solid #d5c796;
                border-radius: 6px;
                padding: 10px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
        """)
        self.detail_browser.setHtml(
            "<div style='text-align: center; color: #795548; padding-top: 50px;'>"
            "<h3>Inspección de LoreBlocks</h3>"
            "<p>Selecciona cualquier elemento en la lista jerárquica para ver el desglose completo de condiciones y efectos.</p>"
            "</div>"
        )
        splitter.addWidget(self.detail_browser)

        # Dimensionar divisor (60% lista jerárquica, 40% detalle)
        splitter.setSizes([650, 450])
        main_layout.addWidget(splitter, stretch=1)

    def _expand_all(self):
        self.tree.expandAll()

    def _collapse_all(self):
        self.tree.collapseAll()

    def _set_filter(self, filter_name: str):
        self.current_filter = filter_name
        self.btn_filter_all.setChecked(filter_name == "ALL")
        self.btn_filter_active.setChecked(filter_name == "ACTIVE")
        self.btn_filter_done.setChecked(filter_name == "DONE")
        self.btn_filter_unknown.setChecked(filter_name == "UNKNOWN")
        self._apply_filters()

    def _on_search_changed(self, text: str):
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_edit.text().strip().lower()

        for b_id, item in self.block_items.items():
            block = self.blocks_by_id.get(b_id)
            if not block:
                continue

            st = block.state.lower()
            match_filter = True
            if self.current_filter == "ACTIVE" and st != "active":
                match_filter = False
            elif self.current_filter == "DONE" and st != "done":
                match_filter = False
            elif self.current_filter == "UNKNOWN" and st not in ["unknown"]:
                match_filter = False

            match_query = True
            if query:
                title_match = query in (block.title or "").lower()
                name_match = query in (block.name or "").lower()
                id_match = query in block.id.lower()
                cond_match = any(query in c.display_text.lower() for c in block.conditions)
                match_query = (title_match or name_match or id_match or cond_match)

            is_visible = match_filter and match_query
            item.setHidden(not is_visible)

            # Si el bloque es visible, asegurar que sus ancestros no queden ocultos
            if is_visible:
                parent_it = item.parent()
                while parent_it:
                    parent_it.setHidden(False)
                    parent_it = parent_it.parent()

    def update_lore_graph(self, projection: Optional[LoreGraphProjection]):
        """Actualiza la lista jerárquica con la proyección actual de LoreBlocks."""
        self.current_projection = projection
        self.tree.clear()
        self.block_items.clear()
        self.blocks_by_id.clear()

        if not projection or not projection.blocks:
            self.lbl_total.setText("Total: 0")
            self.lbl_active.setText("🟢 Activos: 0")
            self.lbl_done.setText("🔵 Completados: 0")
            self.lbl_unknown.setText("🟡 Pendientes: 0")
            return

        # Actualizar contadores
        self.lbl_total.setText(f"Total: {projection.total_count}")
        self.lbl_active.setText(f"🟢 Activos: {projection.active_count}")
        self.lbl_done.setText(f"🔵 Completados: {projection.done_count}")
        self.lbl_unknown.setText(f"🟡 Pendientes: {projection.unknown_count}")

        self.blocks_by_id = {b.id: b for b in projection.blocks}

        # 1. Agrupar por parent_id
        children_map: Dict[Optional[str], List[LoreBlockDetailProjection]] = {}
        for b in projection.blocks:
            p_id = b.parent_id if b.parent_id in self.blocks_by_id else None
            children_map.setdefault(p_id, []).append(b)

        # 2. Construir nodos recursivamente
        def create_block_subtree(block: LoreBlockDetailProjection, parent_item: Optional[QTreeWidgetItem]) -> QTreeWidgetItem:
            item = QTreeWidgetItem(parent_item or self.tree)
            self.block_items[block.id] = item
            item.setData(0, Qt.UserRole, block.id)

            st = block.state.lower()
            is_acc = block.is_accessible

            # Formatear etiqueta con color y símbolo
            if st == "active":
                symbol = "🟢 [ACTIVO]"
                fg_color = QColor("#1b5e20")  # Verde oscuro
                font_weight = QFont.Bold
            elif st == "done":
                symbol = "🔵 [COMPLETADO]"
                fg_color = QColor("#0d47a1")  # Azul
                font_weight = QFont.Bold
            elif not is_acc:
                symbol = "🔒 [BLOQUEADO]"
                fg_color = QColor("#757575")  # Gris
                font_weight = QFont.Normal
            else:
                symbol = "🟡 [PENDIENTE]"
                fg_color = QColor("#e65100")  # Ámbar
                font_weight = QFont.Bold

            title_str = block.title or block.name or block.id
            item_text = f"{symbol}  {title_str}  ({block.id})"
            item.setText(0, item_text)
            item.setForeground(0, fg_color)
            font = item.font(0)
            font.setBold(font_weight == QFont.Bold)
            item.setFont(0, font)

            # Sub-elementos: Condiciones de activación
            cond_count = len(block.conditions)
            met_count = sum(1 for c in block.conditions if c.is_met)

            if cond_count > 0:
                cond_header = QTreeWidgetItem(item)
                status_sum = f"{met_count}/{cond_count} cumplidas"
                cond_header.setText(0, f"  📋 Condiciones de Activación ({status_sum}):")
                cond_header.setForeground(0, QColor("#37474f"))
                f_h = cond_header.font(0)
                f_h.setItalic(True)
                cond_header.setFont(0, f_h)

                for cond in block.conditions:
                    c_item = QTreeWidgetItem(cond_header)
                    if cond.is_met:
                        c_item.setText(0, f"    ✓ [Cumplida] {cond.display_text}")
                        c_item.setForeground(0, QColor("#2e7d32"))
                    else:
                        c_item.setText(0, f"    ✗ [Pendiente] {cond.display_text}")
                        c_item.setForeground(0, QColor("#c62828"))

            elif st == "unknown":
                auto_cond = QTreeWidgetItem(item)
                auto_cond.setText(0, "  ⚡ Sin condiciones (Pasa a Active automáticamente al iniciar)")
                auto_cond.setForeground(0, QColor("#2e7d32"))

            # Sub-elementos: Condiciones de salida
            if block.exit_conditions:
                exit_header = QTreeWidgetItem(item)
                exit_met = sum(1 for c in block.exit_conditions if c.is_met)
                exit_header.setText(0, f"  🏁 Condiciones de Salida ({exit_met}/{len(block.exit_conditions)}):")
                exit_header.setForeground(0, QColor("#1565c0"))

                for cond in block.exit_conditions:
                    c_item = QTreeWidgetItem(exit_header)
                    if cond.is_met:
                        c_item.setText(0, f"    ✓ [Cumplida] {cond.display_text}")
                        c_item.setForeground(0, QColor("#2e7d32"))
                    else:
                        c_item.setText(0, f"    ✗ [Pendiente] {cond.display_text}")
                        c_item.setForeground(0, QColor("#c62828"))

            if getattr(block, "exit_rag_enabled", False) and block.exit_trigger_phrases:
                rag_exit_item = QTreeWidgetItem(item)
                phrases_summary = ", ".join(f"'{p}'" for p in block.exit_trigger_phrases[:3])
                if len(block.exit_trigger_phrases) > 3:
                    phrases_summary += f" (+{len(block.exit_trigger_phrases) - 3} más)"
                rag_exit_item.setText(0, f"  📡 Antenas RAG de Salida: {phrases_summary}")
                rag_exit_item.setForeground(0, QColor("#00695c"))

            # Efectos resumidos
            if block.on_active_summary and block.on_active_summary != "(Sin efectos)":
                eff_item = QTreeWidgetItem(item)
                eff_item.setText(0, f"  🎁 Efectos al activarse: {block.on_active_summary}")
                eff_item.setForeground(0, QColor("#4e342e"))

            # Hijos jerárquicos
            for child in children_map.get(block.id, []):
                create_block_subtree(child, item)

            return item

        # Construir bloques raíz
        root_blocks = children_map.get(None, [])
        for r_b in root_blocks:
            create_block_subtree(r_b, None)

        # Si algún bloque tenía parent_id huérfano, ubicarlo en la raíz
        for b in projection.blocks:
            if b.id not in self.block_items:
                create_block_subtree(b, None)

        # Expandir los bloques raíz por defecto para visualización inmediata
        self.tree.expandAll()
        self._apply_filters()

    def _on_tree_selection_changed(self):
        """Muestra el detalle del bloque seleccionado en el panel lateral."""
        items = self.tree.selectedItems()
        if not items:
            return

        selected_item = items[0]
        # Buscar ID del bloque (subiendo en la jerarquía si se seleccionó una condición hija)
        curr = selected_item
        block_id = None
        while curr:
            b_id = curr.data(0, Qt.UserRole)
            if b_id:
                block_id = b_id
                break
            curr = curr.parent()

        if block_id and block_id in self.blocks_by_id:
            block = self.blocks_by_id[block_id]
            self._display_block_detail(block)

    def _display_block_detail(self, block: LoreBlockDetailProjection):
        """Renderiza la ficha completa en HTML del LoreBlock seleccionado."""
        st = block.state.lower()
        if st == "active":
            status_badge = "<span style='background-color: #2e7d32; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold;'>🟢 ACTIVO</span>"
        elif st == "done":
            status_badge = "<span style='background-color: #1565c0; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold;'>🔵 COMPLETADO (DONE)</span>"
        elif not block.is_accessible:
            status_badge = "<span style='background-color: #757575; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold;'>🔒 BLOQUEADO POR PADRE</span>"
        else:
            status_badge = "<span style='background-color: #ef6c00; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold;'>🟡 PENDIENTE (ACCESIBLE)</span>"

        type_badge = f"<span style='background-color: #e0f2f1; color: #004d40; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-left: 6px;'>Tipo: {block.type}</span>"
        desc_html = f"<div style='color: #4e342e; font-size: 12px; margin-top: 6px; font-style: italic;'>{block.description}</div>" if block.description else ""

        html = f"""
        <div style='font-family: "Segoe UI", sans-serif;'>
            <div style='border-bottom: 2px solid #d5c796; padding-bottom: 8px; margin-bottom: 12px;'>
                <div style='float: right;'>{status_badge}</div>
                <h2 style='margin: 0; color: #3e2b14;'>{block.title or block.id} {type_badge}</h2>
                <div style='color: #666; font-size: 11px; font-family: Consolas; margin-top: 4px;'>ID: {block.id}</div>
                {"<div style='color: #8d6e63; font-size: 11px; margin-top: 2px;'>📁 Bloque Padre: <b>" + block.parent_id + "</b></div>" if block.parent_id else "<div style='color: #558b2f; font-size: 11px; margin-top: 2px;'>🌟 Bloque Raíz (Nivel 0)</div>"}
                {desc_html}
            </div>
        """

        # Sección: Condiciones de Activación (Active)
        html += """
            <h4 style='color: #2e7d32; margin-bottom: 6px; margin-top: 14px;'>
                📋 Condiciones de Activación (Paso a ACTIVE)
            </h4>
        """
        if not block.conditions:
            html += """
                <div style='background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; padding: 8px; color: #1b5e20; font-size: 12px;'>
                    <b>⚡ Sin condiciones de activación</b>: Pasa automáticamente a <code>active</code> al iniciar el juego si sus ancestros están activos.
                </div>
            """
        else:
            html += "<table style='width: 100%; border-collapse: collapse; font-size: 12px;'>"
            for cond in block.conditions:
                if cond.is_met:
                    icon_badge = "<span style='color: #2e7d32; font-weight: bold; font-size: 13px;'>[✓ CUMPLIDA]</span>"
                    row_bg = "#e8f5e9"
                    border = "#a5d6a7"
                else:
                    icon_badge = "<span style='color: #c62828; font-weight: bold; font-size: 13px;'>[✗ PENDIENTE]</span>"
                    row_bg = "#ffebee"
                    border = "#ffcdd2"

                html += f"""
                    <tr style='background-color: {row_bg}; border: 1px solid {border};'>
                        <td style='padding: 6px 8px; width: 110px;'>{icon_badge}</td>
                        <td style='padding: 6px 8px;'><b>{cond.display_text}</b></td>
                    </tr>
                """
            html += "</table>"

        # Sección: Condiciones de Salida (Done)
        html += """
            <h4 style='color: #1565c0; margin-bottom: 6px; margin-top: 14px;'>
                🏁 Condiciones de Salida (Paso a DONE)
            </h4>
        """
        if not block.exit_conditions:
            if getattr(block, "exit_rag_enabled", False):
                phrases_str = ", ".join(f"<i>&laquo;{p}&raquo;</i>" for p in block.exit_trigger_phrases)
                html += f"""
                    <div style='background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; padding: 8px; color: #1b5e20; font-size: 12px;'>
                        <b>📡 Antenas Semánticas RAG de Finalización</b>: Transiciona a <code>done</code> cuando el jugador menciona: {phrases_str}.
                    </div>
                """
            else:
                html += """
                    <div style='background-color: #e3f2fd; border: 1px solid #bbdefb; border-radius: 4px; padding: 8px; color: #0d47a1; font-size: 12px;'>
                        <b>⚡ Sin condiciones de salida</b>: Transiciona inmediatamente a <code>done</code> tras ejecutarse una vez.
                    </div>
                """
        else:
            html += "<table style='width: 100%; border-collapse: collapse; font-size: 12px;'>"
            for cond in block.exit_conditions:
                if cond.is_met:
                    icon_badge = "<span style='color: #2e7d32; font-weight: bold; font-size: 13px;'>[✓ CUMPLIDA]</span>"
                    row_bg = "#e8f5e9"
                    border = "#a5d6a7"
                else:
                    icon_badge = "<span style='color: #c62828; font-weight: bold; font-size: 13px;'>[✗ PENDIENTE]</span>"
                    row_bg = "#ffebee"
                    border = "#ffcdd2"

                html += f"""
                    <tr style='background-color: {row_bg}; border: 1px solid {border};'>
                        <td style='padding: 6px 8px; width: 110px;'>{icon_badge}</td>
                        <td style='padding: 6px 8px;'><b>{cond.display_text}</b></td>
                    </tr>
                """
            html += "</table>"
            if getattr(block, "exit_rag_enabled", False):
                phrases_str = ", ".join(f"<i>&laquo;{p}&raquo;</i>" for p in block.exit_trigger_phrases)
                html += f"""
                    <div style='margin-top: 6px; background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; padding: 8px; color: #1b5e20; font-size: 12px;'>
                        <b>📡 Antenas Semánticas RAG de Finalización</b>: Requiere cumplir las condiciones anteriores Y coincidencia con: {phrases_str}.
                    </div>
                """

        # Sección: Efectos y Mutaciones
        html += """
            <h4 style='color: #3e2b14; margin-bottom: 6px; margin-top: 14px;'>
                🎁 Efectos y Mutaciones (Effects)
            </h4>
        """
        if block.effects:
            html += "<table style='width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 8px;'>"
            for eff in block.effects:
                eff_type = eff.get("type", "unknown")
                details = ", ".join(f"<b>{k}</b>: {v}" for k, v in eff.items() if k != "type")
                html += f"""
                    <tr style='background-color: #fffde7; border: 1px solid #fff59d;'>
                        <td style='padding: 6px 8px; font-weight: bold; color: #f57f17; width: 130px;'>{eff_type}</td>
                        <td style='padding: 6px 8px; color: #424242;'>{details if details else "(sin parámetros)"}</td>
                    </tr>
                """
            html += "</table>"
        elif block.on_active_summary or block.on_done_summary:
            html += f"""
                <div style='background-color: #f5f0d0; border: 1px solid #d5c796; border-radius: 4px; padding: 8px; font-size: 12px; margin-bottom: 6px;'>
                    <b>Al Activarse (on_active):</b> {block.on_active_summary or "(Sin efectos)"}
                </div>
                <div style='background-color: #f5f0d0; border: 1px solid #d5c796; border-radius: 4px; padding: 8px; font-size: 12px;'>
                    <b>Al Completarse (on_done):</b> {block.on_done_summary or "(Sin efectos)"}
                </div>
            """
        else:
            html += "<div style='color: #888; font-size: 12px; font-style: italic;'>Sin efectos configurados</div>"

        # Sección: Directiva Narrativa
        if block.directive:
            html += f"""
                <h4 style='color: #1b5e20; margin-bottom: 6px; margin-top: 14px;'>
                    💬 Directiva Inyectada al LLM
                </h4>
                <div style='background-color: #f1f8e9; border: 1px solid #c5e1a5; border-radius: 4px; padding: 8px; color: #1b5e20; font-style: italic; font-size: 12px;'>
                    "{block.directive}"
                </div>
            """

        # Frases de activación RAG si existen
        if block.trigger_phrases:
            phrases_html = "".join(f"<li><code>{p}</code></li>" for p in block.trigger_phrases)
            html += f"""
                <h4 style='color: #795548; margin-bottom: 6px; margin-top: 14px;'>
                    📡 Frases Gatillo Semánticas (RAG)
                </h4>
                <ul style='font-size: 12px; margin-top: 4px; padding-left: 20px; color: #4e342e;'>
                    {phrases_html}
                </ul>
            """

        html += "</div>"
        self.detail_browser.setHtml(html)
