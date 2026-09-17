import sys
from PySide6.QtWidgets import QApplication
from engines.game.engine import GameEngine
from engines.transformer import TransformerEngine
from game_debugger.app import GameDebuggerApp

# Reutilizar el mismo estilo papiro que el editor para consistencia estética
SEPIA_STYLESHEET = """
QWidget {
    background-color: #f3ebc6;
    color: #3e2b14;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QLineEdit, QTextEdit, QTextBrowser, QTreeWidget, QTableWidget, QListWidget {
    background-color: #faf6df;
    color: #3e2b14;
    border: 1px solid #d5c796;
    border-radius: 4px;
    padding: 3px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #b58238;
}

QHeaderView::section {
    background-color: #e6dca8;
    color: #3e2b14;
    padding: 4px;
    border: 1px solid #d5c796;
}

QPushButton {
    background-color: #e6dca8;
    color: #3e2b14;
    border: 1px solid #d5c796;
    border-radius: 4px;
    padding: 5px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #decfa0;
}

QPushButton:pressed {
    background-color: #d1c18d;
}

QScrollArea {
    background-color: #f3ebc6;
    border: none;
}

QTreeView::item:selected, QTableView::item:selected {
    background-color: #d8c998;
    color: #3e2b14;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #d5c796;
    border-radius: 6px;
    margin-top: 15px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
}

QTabWidget::pane {
    border: 1px solid #d5c796;
    background-color: #f3ebc6;
}

QTabBar::tab {
    background-color: #e6dca8;
    border: 1px solid #d5c796;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 10px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #f3ebc6;
    border-bottom: 1px solid #f3ebc6;
}

QStatusBar {
    background-color: #e6dca8;
    border-top: 1px solid #d5c796;
}
"""

import os
from typing import Any, Optional
from adventure_selector import get_default_adventure_path, open_adventure_selector, set_default_adventure_path
from engines.transformer import create_llm_adapter

LLM_CONFIG_PATH = os.path.join("Resources", "system_data", "llm_config.json")


from engines import AdventureSession

def start_debugger(
    session: Optional[AdventureSession] = None,
    game_engine: Optional[Any] = None,
    dm: Optional[Any] = None,
    aad_path: Optional[str] = None,
):
    """
    Punto de entrada de la aplicación del Depurador Gráfico.
    Inicializa QApplication, aplica el tema y muestra la ventana principal.
    Si no se proporciona sesión ni motor, resuelve la aventura por defecto o solicita
    seleccionar una mediante el selector de aventuras.
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Aplicar estilo sepia
    app.setStyleSheet(SEPIA_STYLESHEET)

    # 1. Si no hay sesión provista pero sí game_engine
    if session is None and game_engine is not None:
        session = AdventureSession(game_engine=game_engine, transformer_engine=dm, aad_path=aad_path)

    # 2. Si no hay sesión ni motor, resolver archivo .aad y arrancar sesión
    if session is None:
        target_path = aad_path or get_default_adventure_path()
        if not target_path or not os.path.exists(target_path):
            target_path = open_adventure_selector()
            if not target_path:
                print("[INFO] Selección de aventura cancelada. Saliendo.")
                return

        try:
            session = AdventureSession.start(target_path)
            aad_path = target_path
            set_default_adventure_path(target_path)
        except Exception as e:
            print(f"[ERROR] Error al inicializar AdventureSession con {target_path}: {e}")
            return

    window = GameDebuggerApp(session=session, aad_path=aad_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start_debugger()

