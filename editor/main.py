import sys
from PySide6.QtWidgets import QApplication
from editor.app import StoryEditorApp

SEPIA_STYLESHEET = """
QWidget {
    background-color: #f3ebc6;
    color: #3e2b14;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTreeWidget, QTableWidget, QListWidget {
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

QMenuBar {
    background-color: #e6dca8;
    border-bottom: 1px solid #d5c796;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
}

QMenuBar::item:selected {
    background-color: #d8c998;
}

QMenu {
    background-color: #faf6df;
    border: 1px solid #d5c796;
}

QMenu::item:selected {
    background-color: #d8c998;
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
"""

def start_editor():
    """
    Punto de entrada de la aplicación PySide6.
    Inicializa QApplication y muestra la interfaz gráfica.
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setStyleSheet(SEPIA_STYLESHEET)

    window = StoryEditorApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    start_editor()
