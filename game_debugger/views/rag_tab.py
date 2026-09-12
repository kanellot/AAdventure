"""Pestaña de inspección semántica RAG para el depurador de juego."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from domains.projections import RagEvaluationProjection


class RagTab(QWidget):
    """
    Vista dedicada a la inspección del enrutamiento semántico RAG:
    Muestra el prompt del jugador en una línea compacta, una vista de texto
    enriquecido (HTML/Markdown) que lista todas las antenas sin truncar
    y una sección inferior compacta con la directiva inyectada.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Barra Superior Compacta (1 sola línea de alto)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        prompt_label = QLabel("Prompt:")
        prompt_label.setStyleSheet("font-weight: bold; color: #3e2b14;")
        self.player_input_edit = QLineEdit()
        self.player_input_edit.setReadOnly(True)
        self.player_input_edit.setPlaceholderText("No hay interacción de texto registrada aún...")

        self.threshold_label = QLabel("Umbral: 0.65")
        self.threshold_label.setStyleSheet("font-weight: bold; color: #795548; padding: 2px 6px;")

        self.status_badge = QLabel("SIN EVALUACIÓN")
        self.status_badge.setStyleSheet(
            "font-weight: bold; padding: 3px 10px; border-radius: 4px; background-color: #e6dca8; color: #555;"
        )

        top_row.addWidget(prompt_label)
        top_row.addWidget(self.player_input_edit, stretch=1)
        top_row.addWidget(self.threshold_label)
        top_row.addWidget(self.status_badge)
        layout.addLayout(top_row)

        # 2. Panel Central: Visualizador de Texto Enriquecido (HTML/Markdown)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #faf6df;
                color: #3e2b14;
                border: 1px solid #d5c796;
                border-radius: 4px;
                padding: 8px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
        """)
        self.browser.setHtml(
            "<p style='color: #795548; font-style: italic;'>Las antenas semánticas evaluadas para cada turno aparecerán aquí.</p>"
        )
        layout.addWidget(self.browser, stretch=1)

        # 3. Barra Inferior Compacta: Directiva Inyectada
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        dir_label = QLabel("Directiva Inyectada:")
        dir_label.setStyleSheet("font-weight: bold; color: #1b5e20;")
        self.directive_edit = QLineEdit()
        self.directive_edit.setReadOnly(True)
        self.directive_edit.setPlaceholderText("(Ninguna directiva reactiva inyectada para este turno)")
        self.directive_edit.setStyleSheet("color: #1b5e20; background-color: #f1f8e9;")

        bottom_row.addWidget(dir_label)
        bottom_row.addWidget(self.directive_edit, stretch=1)
        layout.addLayout(bottom_row)

        self.last_evaluation: Optional[RagEvaluationProjection] = None

    def update_rag_evaluation(self, evaluation: Optional[RagEvaluationProjection]) -> None:
        """Actualiza la vista RAG formateando los datos en HTML/Markdown legible."""
        self.last_evaluation = evaluation

        if not evaluation or not evaluation.antennas:
            input_text = evaluation.player_input if evaluation else ""
            thresh = evaluation.threshold if evaluation else 0.65
            self.player_input_edit.setText(input_text)
            self.threshold_label.setText(f"Umbral: {thresh:.2f}")
            self.status_badge.setText("SIN EVALUACIÓN RAG")
            self.status_badge.setStyleSheet(
                "font-weight: bold; padding: 3px 10px; border-radius: 4px; background-color: #e6dca8; color: #666;"
            )
            self.directive_edit.setText("")
            self.directive_edit.setPlaceholderText("(Sin directiva inyectada)")
            self.browser.setHtml(
                "<p style='color: #888; font-style: italic; padding: 10px;'>"
                "No se evaluaron antenas semánticas en este turno (ej. comando de navegación directo o Lore proactivo)."
                "</p>"
            )
            return

        self.player_input_edit.setText(evaluation.player_input)
        self.threshold_label.setText(f"Umbral: {evaluation.threshold:.2f}")

        # Configurar badges y directiva inferior
        if evaluation.matched_lore_id:
            self.status_badge.setText("✓ COINCIDENCIA INYECTADA")
            self.status_badge.setStyleSheet(
                "font-weight: bold; padding: 3px 10px; border-radius: 4px; background-color: #c8e6c9; color: #1b5e20;"
            )
            self.directive_edit.setText(evaluation.injected_directive or "")
            self.directive_edit.setStyleSheet("color: #1b5e20; background-color: #e8f5e9; font-weight: bold;")
        else:
            self.status_badge.setText("SIN COINCIDENCIA")
            self.status_badge.setStyleSheet(
                "font-weight: bold; padding: 3px 10px; border-radius: 4px; background-color: #ffcdd2; color: #b71c1c;"
            )
            self.directive_edit.setText("")
            self.directive_edit.setPlaceholderText("(Ninguna directiva superó el umbral)")
            self.directive_edit.setStyleSheet("color: #555; background-color: #faf6df;")

        # Construir contenido HTML enriquecido con ajuste de línea
        html = []

        # Tarjeta destacada de la coincidencia inyectada si existe
        if evaluation.matched_lore_id:
            html.append(f"""
            <div style="background-color: #e8f5e9; border: 1px solid #81c784; border-radius: 6px; padding: 10px; margin-bottom: 12px;">
                <div style="font-size: 14px; font-weight: bold; color: #1b5e20;">
                    ✓ Clasificación Ganadora: &ldquo;{evaluation.matched_antenna}&rdquo;
                </div>
                <div style="color: #2e7d32; margin-top: 4px; font-size: 12px;">
                    <b>Bloque de Lore:</b> {evaluation.matched_lore_id} &nbsp;|&nbsp; <b>Umbral Mínimo:</b> {evaluation.threshold:.2f}
                </div>
                <div style="margin-top: 6px; padding: 6px 10px; background-color: #ffffff; border-left: 4px solid #4caf50; border-radius: 3px; color: #2e7d32;">
                    <b>Directiva inyectada al LLM:</b> {evaluation.injected_directive}
                </div>
            </div>
            """)

        # Agrupar antenas por LoreBlock
        blocks_dict = {}
        for ant in evaluation.antennas:
            key = ant.lore_id
            if key not in blocks_dict:
                blocks_dict[key] = {
                    "lore_id": ant.lore_id,
                    "lore_title": ant.lore_title,
                    "conditions_met": ant.conditions_met,
                    "has_match": False,
                    "max_score": 0.0,
                    "antennas": [],
                }
            blocks_dict[key]["antennas"].append(ant)
            if ant.is_matched and ant.is_injected:
                blocks_dict[key]["has_match"] = True
            if ant.score > blocks_dict[key]["max_score"]:
                blocks_dict[key]["max_score"] = ant.score

        # Ordenar bloques: primero el que tiene match inyectado, luego por max_score descendente
        sorted_blocks = sorted(
            blocks_dict.values(),
            key=lambda b: (1 if b["has_match"] else 0, b["max_score"]),
            reverse=True,
        )

        for block in sorted_blocks:
            has_match = block["has_match"]
            cond_met = block["conditions_met"]

            if has_match:
                block_border = "#81c784"
                header_bg = "#e8f5e9"
                header_fg = "#1b5e20"
                block_badge = "<span style='background-color: #2e7d32; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>✓ INYECTADO</span>"
            elif not cond_met:
                block_border = "#d5c796"
                header_bg = "#e6dca8"
                header_fg = "#795548"
                block_badge = "<span style='background-color: #ef9a9a; color: #b71c1c; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>CONDICIONES NO CUMPLIDAS</span>"
            elif block["max_score"] >= evaluation.threshold:
                block_border = "#d5c796"
                header_bg = "#fff9c4"
                header_fg = "#795548"
                block_badge = f"<span style='background-color: #ffe082; color: #e65100; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>SUPERA UMBRAL ({block['max_score']:.4f})</span>"
            else:
                block_border = "#d5c796"
                header_bg = "#e6dca8"
                header_fg = "#3e2b14"
                block_badge = f"<span style='background-color: #d7ccc8; color: #4e342e; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>BAJO UMBRAL (máx {block['max_score']:.4f})</span>"

            html.append(f"""
            <div style="background-color: #faf6df; border: 1px solid {block_border}; border-radius: 6px; margin-bottom: 14px;">
                <div style="background-color: {header_bg}; padding: 7px 10px; border-bottom: 1px solid {block_border};">
                    <span style="font-weight: bold; font-size: 13px; color: {header_fg};">
                        📦 Bloque: {block['lore_title']}
                    </span>
                    <span style="color: #777; font-size: 11px; margin-left: 6px;">(ID: {block['lore_id']})</span>
                    <span style="float: right;">{block_badge}</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="background-color: #f3ebc6; color: #6d4c41; text-align: left; font-size: 11px; border-bottom: 1px solid #e0d7b0;">
                            <th style="padding: 5px 8px; width: 60%;">Antena (Frase Gatillo)</th>
                            <th style="padding: 5px 8px; text-align: center; width: 14%;">Similitud</th>
                            <th style="padding: 5px 8px; text-align: center; width: 13%;">Condiciones</th>
                            <th style="padding: 5px 8px; text-align: center; width: 13%;">Estado</th>
                        </tr>
                    </thead>
                    <tbody>
            """)

            # Ordenar antenas dentro del bloque por score descendente
            block_antennas = sorted(block["antennas"], key=lambda a: a.score, reverse=True)

            for ant in block_antennas:
                if ant.is_matched and ant.is_injected:
                    row_bg = "#c8e6c9"
                    row_fg = "#1b5e20"
                    badge = "<span style='background-color: #2e7d32; color: #fff; padding: 2px 6px; border-radius: 3px; font-weight: bold;'>✓ INYECTADO</span>"
                elif not ant.conditions_met:
                    row_bg = "#faf6df"
                    row_fg = "#888888"
                    badge = "<span style='color: #888;'>Cond. no cumplidas</span>"
                elif ant.score < ant.threshold:
                    row_bg = "#faf6df"
                    row_fg = "#555555"
                    badge = "<span style='color: #777;'>Bajo umbral</span>"
                else:
                    row_bg = "#fff9c4"
                    row_fg = "#795548"
                    badge = "<span style='color: #e65100; font-weight: bold;'>Supera umbral</span>"

                cond_str = "<span style='color: #2e7d32;'>✓ Sí</span>" if ant.conditions_met else "<span style='color: #c62828;'>✗ No</span>"

                html.append(f"""
                    <tr style="background-color: {row_bg}; color: {row_fg}; border-bottom: 1px solid #e8dfbe;">
                        <td style="padding: 5px 8px; font-weight: {'bold' if ant.is_matched else 'normal'};">&ldquo;{ant.antenna}&rdquo;</td>
                        <td style="padding: 5px 8px; text-align: center; font-weight: bold;">{ant.score:.4f}</td>
                        <td style="padding: 5px 8px; text-align: center;">{cond_str}</td>
                        <td style="padding: 5px 8px; text-align: center;">{badge}</td>
                    </tr>
                """)

            html.append("""
                    </tbody>
                </table>
            </div>
            """)

        self.browser.setHtml("".join(html))
