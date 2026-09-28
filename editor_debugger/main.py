import os
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication

from adventure_selector import (
    get_default_adventure_path,
    set_default_adventure_path,
)
from editor_debugger.app import EditorDebuggerApp, SEPIA_STYLESHEET

DEFAULT_AAD_PATH = os.path.join("Resources", "adventure_data", "Adventure.aad")


def start_editor_debugger(mode: str = "editor", aad_path: Optional[str] = None):
    """Punto de entrada de la suite unificada Editor-Debugger.

    Inicializa QApplication con la hoja de estilos sepia, resuelve la ruta de la aventura
    y despliega la ventana principal seleccionando la pestaña inicial solicitada.
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setStyleSheet(SEPIA_STYLESHEET)

    target_path = aad_path
    if not target_path or not os.path.exists(target_path):
        default_candidate = get_default_adventure_path() or DEFAULT_AAD_PATH
        if os.path.exists(default_candidate):
            target_path = default_candidate

    window = EditorDebuggerApp(mode=mode, aad_path=target_path)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    start_editor_debugger()
