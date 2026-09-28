import os
import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from editor_debugger.editor.app import StoryEditorApp
from editor_debugger.debugger.app import GameDebuggerApp
from adventure_selector import get_default_adventure_path


SEPIA_STYLESHEET = """
QWidget {
    background-color: #f3ebc6;
    color: #3e2b14;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QLineEdit, QTextEdit, QTextBrowser, QTreeWidget, QTableWidget, QListWidget, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #faf6df;
    color: #3e2b14;
    border: 1px solid #d5c796;
    border-radius: 4px;
    padding: 3px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
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
    padding: 6px 13px;
    margin-right: 3px;
    font-weight: bold;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #f3ebc6;
    border-bottom: 1px solid #f3ebc6;
}

QTabBar::tab:hover:!selected {
    background-color: #decfa0;
}

QStatusBar {
    background-color: #e6dca8;
    border-top: 1px solid #d5c796;
}
"""


class FloatingDebuggerWindow(QMainWindow):
    """Ventana flotante independiente para visualizar el Depurador desacoplado."""

    def __init__(self, parent_suite: "EditorDebuggerApp", debugger_app: GameDebuggerApp):
        super().__init__()
        self.parent_suite = parent_suite
        self.debugger_app = debugger_app
        self.setWindowTitle("Depurador de Juego - AAdventure (Ventana Flotante)")
        self.resize(1150, 780)

        # Barra superior con botones de control y reacoplar
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(6)

        self.reload_btn = QPushButton("🔄 Recargar")
        self.reload_btn.setToolTip("Guarda la historia en el editor e inicia la partida en el depurador (Ctrl+R)")
        self.reload_btn.setShortcut("Ctrl+R")
        self.reload_btn.setStyleSheet("""
            QPushButton {
                color: #0d47a1;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.reload_btn.clicked.connect(self.parent_suite.reload_and_play_debugger)
        top_layout.addWidget(self.reload_btn)

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setToolTip("Iniciar la partida en el depurador (Turno 0)")
        self.start_btn.setStyleSheet("""
            QPushButton {
                color: #1b5e20;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.start_btn.clicked.connect(self.parent_suite.start_debugger_adventure)
        top_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setToolTip("Detener la partida en el depurador")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                color: #b71c1c;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.stop_btn.clicked.connect(self.parent_suite.stop_debugger_adventure)
        top_layout.addWidget(self.stop_btn)

        # Sincronizar estado inicial
        is_running = getattr(self.debugger_app, "is_running", False)
        self.update_buttons_state(is_running)

        btn_reattach = QPushButton("📥 Reacoplar en Ventana Principal")
        btn_reattach.setToolTip("Devuelve el depurador a la pestaña de la ventana principal")
        btn_reattach.clicked.connect(self.close)
        top_layout.addStretch()
        top_layout.addWidget(btn_reattach)

        # Contenedor central
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(top_bar)
        layout.addWidget(self.debugger_app)

        self.setCentralWidget(container)

    def update_buttons_state(self, is_running: bool):
        """Actualiza el estado habilitado/deshabilitado de los botones Start, Stop y Recargar."""
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.reload_btn.setEnabled(True)

    def closeEvent(self, event):
        """Al cerrar la ventana flotante, reacopla el depurador en la suite."""
        self.parent_suite.reattach_debugger()
        event.accept()


class EditorDebuggerApp(QMainWindow):
    """Ventana principal unificada que integra el Editor de Historias y el Depurador de Juego.

    Proporciona conmutación mediante pestañas superiores fijas, sincronización guiada de
    cambios entre ambas herramientas y capacidad de desacoplamiento para visualización
    simultánea en paralelo.
    """

    def __init__(
        self,
        mode: str = "editor",
        aad_path: Optional[str] = None,
    ):
        super().__init__()
        self.setWindowTitle("AAdventure Studio - Editor & Debugger")
        self.resize(1200, 800)

        self.initial_aad_path = aad_path or get_default_adventure_path()
        self.floating_window: Optional[FloatingDebuggerWindow] = None
        self._is_switching_tabs: bool = False
        self.debugger_app: Optional[GameDebuggerApp] = None
        self.debugger_placeholder = QWidget()

        # 1. Contenedor de pestañas principal
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.setCentralWidget(self.tab_widget)

        # 2. Inicializar el Editor de Historias
        self.editor_app = StoryEditorApp()
        self.editor_app.setWindowFlags(Qt.Widget)
        self.editor_app.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tab_widget.addTab(self.editor_app, "✏️ Editor de Historias")

        # 3. Inicializar el Depurador de Juego de forma completa desde el arranque (Eager Initialization)
        self._ensure_debugger_initialized()

        # 4. Botones de esquina superior derecha (Recargar, Start, Stop y Desacoplar)
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 4, 0)
        corner_layout.setSpacing(6)

        self.reload_btn = QPushButton("🔄 Recargar")
        self.reload_btn.setToolTip("Guarda la historia en el editor e inicia la partida en el depurador (Ctrl+R)")
        self.reload_btn.setShortcut("Ctrl+R")
        self.reload_btn.setStyleSheet("""
            QPushButton {
                color: #0d47a1;
                font-weight: bold;
                padding: 5px 12px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.reload_btn.clicked.connect(self.reload_and_play_debugger)
        self.reload_btn.setEnabled(True)
        corner_layout.addWidget(self.reload_btn)

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setToolTip("Iniciar la partida en el depurador (Turno 0) (F5)")
        self.start_btn.setShortcut("F5")
        self.start_btn.setStyleSheet("""
            QPushButton {
                color: #1b5e20;
                font-weight: bold;
                padding: 5px 12px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.start_btn.clicked.connect(self.start_debugger_adventure)
        self.start_btn.setEnabled(True)  # El depurador arranca en STOP por defecto
        corner_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setToolTip("Detener la partida en el depurador (Shift+F5)")
        self.stop_btn.setShortcut("Shift+F5")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                color: #b71c1c;
                font-weight: bold;
                padding: 5px 12px;
            }
            QPushButton:disabled {
                color: #9e9e9e;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_debugger_adventure)
        self.stop_btn.setEnabled(False)
        corner_layout.addWidget(self.stop_btn)

        self.detach_btn = QPushButton("⧉ Desacoplar Depurador")
        self.detach_btn.setToolTip("Abre el depurador en una ventana independiente para ver ambos a la vez")
        self.detach_btn.clicked.connect(self.toggle_debugger_detachment)
        corner_layout.addWidget(self.detach_btn)

        self.tab_widget.setCornerWidget(corner_widget, Qt.TopRightCorner)

        # 5. Conectar señales del editor tras tener los botones y depurador inicializados
        self.editor_app.story_loaded.connect(self._on_editor_story_loaded)
        self.editor_app.story_saved.connect(self._on_editor_story_saved)

        if self.initial_aad_path and os.path.exists(self.initial_aad_path):
            try:
                self.editor_app.load_story_file(self.initial_aad_path)
            except Exception as e:
                print(f"[WARN] No se pudo precargar {self.initial_aad_path} en el editor: {e}")

        # 5. Conectar evento de conmutación de pestañas
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Seleccionar pestaña inicial
        if mode == "debugger":
            self.tab_widget.setCurrentIndex(1)
        else:
            self.tab_widget.setCurrentIndex(0)
        self._update_title()

    def _get_active_aad_path(self) -> Optional[str]:
        """Obtiene la ruta actual del archivo .aad según el editor o ruta por defecto."""
        path = getattr(self.editor_app.controller, "current_file_path", None)
        if path and os.path.exists(path):
            return path
        if self.initial_aad_path and os.path.exists(self.initial_aad_path):
            return self.initial_aad_path
        default_path = get_default_adventure_path()
        if default_path and os.path.exists(default_path):
            return default_path
        return None

    def _ensure_debugger_initialized(self):
        """Inicializa GameDebuggerApp al arranque o bajo demanda."""
        if self.debugger_app is not None:
            return

        aad = self._get_active_aad_path()
        try:
            self.debugger_app = GameDebuggerApp(aad_path=aad, auto_start=False)
            self.debugger_app.adventure_state_changed.connect(self._on_debugger_state_changed)
            self.debugger_app.setWindowFlags(Qt.Widget)
            self.debugger_app.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # Reemplazar placeholder por el depurador real en el tab si existe
            idx_ph = self.tab_widget.indexOf(self.debugger_placeholder)
            if idx_ph != -1:
                self._is_switching_tabs = True
                self.tab_widget.removeTab(idx_ph)
                self.tab_widget.insertTab(idx_ph, self.debugger_app, "🐞 Depurador de Juego")
                self._is_switching_tabs = False
            elif self.tab_widget.indexOf(self.debugger_app) == -1:
                self.tab_widget.addTab(self.debugger_app, "🐞 Depurador de Juego")

            # Sincronizar estado inicial de los botones
            is_running = getattr(self.debugger_app, "is_running", False)
            self._on_debugger_state_changed(is_running)
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar GameDebuggerApp: {e}")
            if self.tab_widget.indexOf(self.debugger_placeholder) == -1 and self.tab_widget.indexOf(self.debugger_app) == -1:
                self.tab_widget.addTab(self.debugger_placeholder, "🐞 Depurador de Juego")

    def reload_and_play_debugger(self):
        """Guarda la historia en el editor e inicia automáticamente la partida en el depurador."""
        # 1. Guardar la historia en el editor (valida integridad)
        saved = self.editor_app.on_save_story()
        if not saved:
            return

        # 2. Obtener la ruta activa guardada
        active_path = self._get_active_aad_path()
        if not active_path or not os.path.exists(active_path):
            QMessageBox.warning(self, "Aviso", "No hay un archivo .aad guardado válido para ejecutar.")
            return

        # 3. Arrancar la partida en el depurador (Turno 0)
        if not self.debugger_app:
            self._ensure_debugger_initialized()
        self.debugger_app.start_adventure(active_path)

    def start_debugger_adventure(self):
        """Inicia la partida en el depurador cargando los datos guardados en disco (Turno 0)."""
        if not self.debugger_app:
            self._ensure_debugger_initialized()
            return

        aad_path = self._get_active_aad_path()
        if not aad_path or not os.path.exists(aad_path):
            QMessageBox.warning(self, "Aviso", "No hay un archivo .aad guardado válido para ejecutar.")
            return

        self.debugger_app.start_adventure(aad_path)

    def stop_debugger_adventure(self):
        """Detiene la partida en el depurador."""
        if self.debugger_app:
            self.debugger_app.stop_adventure()

    def reload_debugger_adventure(self):
        """Alias para reiniciar o iniciar la partida en el depurador."""
        self.reload_and_play_debugger()

    def _on_editor_story_loaded(self, aad_path: str):
        """Reacciona a la carga de una nueva historia en el editor manteniendo el depurador sincronizado y en STOP."""
        if aad_path:
            self.initial_aad_path = aad_path
        if getattr(self, "debugger_app", None):
            self.debugger_app.set_adventure_path(aad_path)
        if hasattr(self, "start_btn") and hasattr(self, "stop_btn"):
            self._on_debugger_state_changed(False)

    def _on_editor_story_saved(self, aad_path: str):
        """Reacciona al guardado de una historia en el editor actualizando la ruta activa."""
        if aad_path:
            self.initial_aad_path = aad_path
            if getattr(self, "debugger_app", None) and not getattr(self.debugger_app, "is_running", False):
                self.debugger_app.aad_path = aad_path
                self.debugger_app.update_window_title()

    def _on_debugger_state_changed(self, is_running: bool):
        """Sincroniza el estado de los botones Start, Stop y Recargar según el estado del depurador."""
        if hasattr(self, "start_btn") and hasattr(self, "stop_btn"):
            self.start_btn.setEnabled(not is_running)
            self.stop_btn.setEnabled(is_running)
        if hasattr(self, "reload_btn"):
            self.reload_btn.setEnabled(True)
        if self.floating_window:
            self.floating_window.update_buttons_state(is_running)

    def on_tab_changed(self, index: int):
        """Gestiona la transición de pestañas y la actualización de títulos sin alterar la partida activa."""
        if self._is_switching_tabs:
            return

        self._update_title()
        curr_widget = self.tab_widget.currentWidget()
        if curr_widget:
            curr_widget.resize(self.tab_widget.contentsRect().size())
            curr_widget.updateGeometry()

    def resizeEvent(self, event):
        """Asegura que el widget activo en las pestañas se ajuste al espacio completo disponible."""
        super().resizeEvent(event)
        curr_widget = self.tab_widget.currentWidget()
        if curr_widget:
            curr_widget.resize(self.tab_widget.contentsRect().size())
            curr_widget.updateGeometry()

    def _update_title(self):
        """Actualiza el título principal de la ventana según la pestaña activa."""
        if self.tab_widget.currentIndex() == 0:
            sub = "Editor de Historias"
        else:
            sub = "Depurador de Juego"
        self.setWindowTitle(f"AAdventure Studio - {sub}")

    def toggle_debugger_detachment(self):
        """Conmuta entre modo acoplado en pestaña y ventana flotante independiente."""
        if self.floating_window is not None:
            self.reattach_debugger()
        else:
            self.detach_debugger()

    def detach_debugger(self):
        """Desacopla el Depurador a una ventana flotante independiente preservando la partida activa."""
        self._ensure_debugger_initialized()
        if not self.debugger_app:
            QMessageBox.warning(self, "Depurador", "No se pudo inicializar el depurador.")
            return

        # Quitar la pestaña del depurador o su placeholder del tab_widget
        idx = self.tab_widget.indexOf(self.debugger_app)
        if idx != -1:
            self.tab_widget.removeTab(idx)
        idx_ph = self.tab_widget.indexOf(self.debugger_placeholder)
        if idx_ph != -1:
            self.tab_widget.removeTab(idx_ph)

        # Crear y mostrar ventana flotante
        self.floating_window = FloatingDebuggerWindow(self, self.debugger_app)
        self.floating_window.show()
        self.detach_btn.setText("📥 Reacoplar Depurador")
        self.detach_btn.setToolTip("Devuelve el depurador a la pestaña principal")

    def reattach_debugger(self):
        """Reincorpora el Depurador a las pestañas de la ventana principal."""
        if self.floating_window is not None:
            self.floating_window.debugger_app.setParent(None)
            self.floating_window = None

        if self.debugger_app is not None:
            # Asegurarse de limpiar placeholder si existiera
            idx_ph = self.tab_widget.indexOf(self.debugger_placeholder)
            if idx_ph != -1:
                self.tab_widget.removeTab(idx_ph)
            # Reinsertar en la posición 1 si no está presente
            if self.tab_widget.indexOf(self.debugger_app) == -1:
                self.tab_widget.insertTab(1, self.debugger_app, "🐞 Depurador de Juego")
            self.tab_widget.setCurrentIndex(1)

        self.detach_btn.setText("⧉ Desacoplar Depurador")
        self.detach_btn.setToolTip("Abre el depurador en una ventana independiente para ver ambos a la vez")

    def closeEvent(self, event):
        """Libera los recursos y procesos en segundo plano al cerrar."""
        is_interactive = self.isVisible() and "unittest" not in sys.modules and not os.environ.get("TESTING")
        if is_interactive and self.editor_app.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Salir de AAdventure Studio",
                "Hay cambios sin guardar en la historia.\n¿Deseas salir sin guardar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

        if self.floating_window is not None:
            self.floating_window.close()

        if self.debugger_app and hasattr(self.debugger_app, "session") and self.debugger_app.session:
            try:
                self.debugger_app.session.close()
            except Exception:
                pass

        event.accept()
