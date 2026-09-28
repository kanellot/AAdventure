"""Adaptador de eventos Qt para la interfaz gráfica del Game Debugger.

Puente entre el worker thread agnóstico de AdventureSession y el bucle de eventos
de PySide6. Emite señales de Qt para garantizar que la UI se actualice de forma segura
exclusivamente en el hilo gráfico principal.
"""

from PySide6.QtCore import QObject, Signal
from engines.events import EngineEventListener


class QtEngineListener(QObject):
    """Implementa EngineEventListener emitiendo señales Qt seguras para la GUI.
    
    Todas las cargas útiles viajan como cadenas JSON puras ('str') garantizando
    desacoplamiento total con respecto a las clases internas de Python.
    """

    # Señales Qt con payloads JSON puros:
    # thinking_changed: event_json
    thinking_changed = Signal(str)
    # task_completed: task_id, result_json
    task_completed = Signal(str, str)
    # state_updated: ui_state_json
    state_updated = Signal(str)
    # task_error: task_id, error_message, error_code
    task_error = Signal(str, str, str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

    def on_thinking_changed(self, event_json: str) -> None:
        """Despacha el cambio de estado Thinking a la cola de eventos de Qt."""
        self.thinking_changed.emit(event_json)

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        """Despacha el resultado del turno completado a la cola de eventos de Qt."""
        self.task_completed.emit(task_id, result_json)

    def on_state_updated(self, ui_state_json: str) -> None:
        """Despacha la actualización de estado consolidado a la cola de eventos de Qt."""
        self.state_updated.emit(ui_state_json)

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        """Despacha la notificación de error a la cola de eventos de Qt."""
        self.task_error.emit(task_id, error_message, error_code)
