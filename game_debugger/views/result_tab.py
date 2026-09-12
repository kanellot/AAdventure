"""Pestaña de resultado narrativo y de motor para el depurador de juego."""

from typing import Optional
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from domains.projections import TurnResultProjection


class ResultTab(QWidget):
    """
    Vista dedicada a inspeccionar el resultado completo del turno:
    - La narración devuelta al jugador y su autor.
    - El resultado estructurado generado por el motor de juego.
    - Las respuestas raw y JSON estructurado del LLM.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Panel Superior: Narración y Mensaje del DM / NPC
        narrative_group = QGroupBox("Respuesta Narrativa del Juego")
        narrative_layout = QVBoxLayout(narrative_group)

        author_row = QHBoxLayout()
        self.author_label = QLabel("Autor: Ninguno")
        self.author_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #b58238;")
        self.info_msg_label = QLabel("")
        self.info_msg_label.setStyleSheet("color: #1565C0; font-style: italic;")

        author_row.addWidget(self.author_label)
        author_row.addStretch()
        author_row.addWidget(self.info_msg_label)
        narrative_layout.addLayout(author_row)

        self.narrative_edit = QTextEdit()
        self.narrative_edit.setReadOnly(True)
        self.narrative_edit.setPlaceholderText("Aquí se mostrará el mensaje narrativo devuelto por el motor...")
        self.narrative_edit.setMinimumHeight(110)
        narrative_layout.addWidget(self.narrative_edit)

        layout.addWidget(narrative_group, stretch=1)

        # 2. Panel Inferior: Detalles Técnicos del Motor y LLM
        tech_group = QGroupBox("Detalle de Ejecución del Motor y Modelo")
        tech_layout = QVBoxLayout(tech_group)

        self.sub_tabs = QTabWidget()

        # Sub-pestaña 1: Resultado del Engine (Mutaciones, Estado)
        self.engine_result_edit = QTextEdit()
        self.engine_result_edit.setReadOnly(True)
        self.engine_result_edit.setFontFamily("Consolas")
        self.engine_result_edit.setPlaceholderText("Resultado devuelto por el GameEngine (mutaciones, afinidad, inventario)...")
        self.sub_tabs.addTab(self.engine_result_edit, "Resultado del Motor")

        # Sub-pestaña 2: Structured JSON
        self.structured_response_edit = QTextEdit()
        self.structured_response_edit.setReadOnly(True)
        self.structured_response_edit.setFontFamily("Consolas")
        self.structured_response_edit.setPlaceholderText("Respuesta validada y estructurada (JSON)...")
        self.sub_tabs.addTab(self.structured_response_edit, "JSON Estructurado")

        # Sub-pestaña 3: Raw Response
        self.raw_response_edit = QTextEdit()
        self.raw_response_edit.setReadOnly(True)
        self.raw_response_edit.setFontFamily("Consolas")
        self.raw_response_edit.setPlaceholderText("Respuesta cruda (Raw) recibida del LLM...")
        self.sub_tabs.addTab(self.raw_response_edit, "Respuesta Cruda (Raw)")

        tech_layout.addWidget(self.sub_tabs)
        layout.addWidget(tech_group, stretch=2)

    def update_result(self, turn_result: Optional[TurnResultProjection]) -> None:
        """Actualiza la vista con los resultados del turno."""
        if not turn_result:
            self.author_label.setText("Autor: Ninguno")
            self.info_msg_label.setText("")
            self.narrative_edit.setPlainText("")
            self.engine_result_edit.setPlainText("")
            self.structured_response_edit.setPlainText("")
            self.raw_response_edit.setPlainText("")
            return

        self.author_label.setText(f"Autor: {turn_result.author}")
        self.info_msg_label.setText(f"Info: {turn_result.info_msg}" if turn_result.info_msg else "")
        self.narrative_edit.setPlainText(turn_result.msg or "(Sin narración devuelta)")
        self.engine_result_edit.setPlainText(turn_result.debug_engine_result or "(No disponible)")
        self.structured_response_edit.setPlainText(turn_result.debug_structured_response or "(No disponible)")
        self.raw_response_edit.setPlainText(turn_result.debug_raw_response or "(No disponible)")
