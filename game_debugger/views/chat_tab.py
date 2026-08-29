from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton
from PySide6.QtCore import Signal

class ChatTab(QWidget):
    """
    Pestaña principal de juego que muestra el historial de chat con colores
    estilizados de acuerdo al tema pergamino, e incluye la entrada de texto.
    """
    send_input = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # 1. Historial del Chat
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(True)
        layout.addWidget(self.chat_browser)

        # 2. Barra de entrada de comandos inferior
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Escribe tu acción o diálogo aquí (ej. 'ir al norte', 'hablar con mendigo')...")
        self.input_edit.returnPressed.connect(self.on_send)
        
        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.on_send)

        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

    def append_message(self, author: str, text: str):
        """
        Añade un mensaje formateado con colores al navegador del chat.
        """
        # Limpiar texto de saltos excesivos y formatear a HTML
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

    def on_send(self):
        text = self.input_edit.text().strip()
        if text:
            self.input_edit.clear()
            self.send_input.emit(text)

    def set_input_enabled(self, enabled: bool):
        self.input_edit.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.input_edit.setFocus()
