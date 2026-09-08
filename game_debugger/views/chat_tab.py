from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton, QComboBox
)
from PySide6.QtCore import Signal
from domains import ActionCommand


class ChatTab(QWidget):
    """
    Pestaña principal de juego que muestra el historial de chat con colores
    estilizados de acuerdo al tema pergamino, e incluye la entrada de texto
    y los botones de comandos directos para depuración.
    """
    send_input = Signal(str)
    send_action = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_game_state = "EXPLORE"

        layout = QVBoxLayout(self)

        # 1. Historial del Chat
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(True)
        layout.addWidget(self.chat_browser)

        # 2. Barra de acciones directas (MOVE, TALK + Target Dropdown)
        action_layout = QHBoxLayout()
        
        self.btn_move = QPushButton("MOVE")
        self.btn_move.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        self.btn_move.clicked.connect(lambda: self.on_action_btn_clicked("MOVE"))
        action_layout.addWidget(self.btn_move)

        self.btn_talk = QPushButton("TALK")
        self.btn_talk.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        self.btn_talk.clicked.connect(lambda: self.on_action_btn_clicked("TALK"))
        action_layout.addWidget(self.btn_talk)

        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(220)
        self.target_combo.setPlaceholderText("Selecciona objetivo...")
        action_layout.addWidget(self.target_combo)

        layout.addLayout(action_layout)

        # 3. Barra de entrada de comandos / diálogo inferior
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setEnabled(False)
        self.input_edit.setPlaceholderText("Selecciona objetivo y pulsa un botón de acción (MOVE, TALK)...")
        self.input_edit.returnPressed.connect(self.on_return_pressed)
        
        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.on_send)
        # Oculto y deshabilitado inicialmente (solo visible en estado TALK)
        self.send_btn.setVisible(False)
        self.send_btn.setEnabled(False)

        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

    def set_targets(self, targets: List[str]):
        """
        Puebla el menú desplegable con los nombres de las entidades disponibles (places y npcs).
        """
        current_selection = self.target_combo.currentText()
        self.target_combo.clear()
        for t in targets:
            self.target_combo.addItem(t)
        if current_selection and current_selection in targets:
            self.target_combo.setCurrentText(current_selection)

    def set_game_state(self, state: str):
        """
        Actualiza la interfaz según el estado de juego (EXPLORE o TALK).
        Habilita el textbox y botón Enviar únicamente si estamos en TALK.
        """
        self.current_game_state = state.upper()
        is_talk = (self.current_game_state == "TALK")
        self.send_btn.setVisible(is_talk)
        self.send_btn.setEnabled(is_talk)
        self.input_edit.setEnabled(is_talk)

        if is_talk:
            self.input_edit.setPlaceholderText("Escribe tu respuesta o frase para el NPC...")
            self.input_edit.setFocus()
        else:
            self.input_edit.clear()
            self.input_edit.setPlaceholderText("Selecciona objetivo y pulsa un botón de acción (MOVE, TALK)...")

    def append_message(self, author: str, text: str):
        """
        Añade un mensaje formateado con colores al navegador del chat.
        """
        formatted_text = text.replace("\n", "<br/>")

        if author == "Dungeon Master":
            html = f"<div style='margin-bottom: 12px; line-height: 1.4;'><b>[DM] Dungeon Master:</b><br/>{formatted_text}</div>"
        elif author == "SYSTEM":
            html = f"<div style='margin-bottom: 12px; color: #b22222; font-family: monospace;'><b>[SISTEMA]:</b> {formatted_text}</div>"
        elif author in ["Aventurero", "Jugador", "Player"]:
            html = f"<div style='margin-bottom: 12px; color: #cb4b16;'><b>[Tú] {author}:</b> {formatted_text}</div>"
        else:
            # Diálogo de NPCs
            html = f"<div style='margin-bottom: 12px; color: #859900;'><b>[NPC] {author}:</b><br/><i>\"{formatted_text}\"</i></div>"

        self.chat_browser.append(html)

    def on_action_btn_clicked(self, action: str):
        """
        Crea un objeto ActionCommand y emite la señal send_action.
        """
        target = self.target_combo.currentText().strip()
        if not target:
            return

        text = self.input_edit.text().strip()
        self.input_edit.clear()

        action_obj = ActionCommand(action=action, target=target)
        self.send_action.emit(action_obj, text)

    def on_return_pressed(self):
        """
        Maneja la pulsación de la tecla Enter en el cuadro de texto.
        Solo envía mensaje si estamos en estado TALK.
        """
        if self.current_game_state == "TALK":
            self.on_send()

    def on_send(self):
        """
        Envía el texto del diálogo actual en estado TALK.
        """
        text = self.input_edit.text().strip()
        if text:
            self.input_edit.clear()
            self.send_input.emit(text)

    def set_input_enabled(self, enabled: bool):
        self.btn_move.setEnabled(enabled)
        self.btn_talk.setEnabled(enabled)
        self.target_combo.setEnabled(enabled)

        is_talk = (self.current_game_state == "TALK")
        self.input_edit.setEnabled(enabled and is_talk)
        self.send_btn.setEnabled(enabled and is_talk)
        if enabled and is_talk:
            self.input_edit.setFocus()
