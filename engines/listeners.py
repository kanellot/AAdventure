"""Protocolo de observadores y listeners para la comunicación reactiva Motor-UI.

Define las interfaces agnósticas de plataforma para desacoplar el bucle de ejecución
del motor y notificar a los clientes (PySide6, Android Kotlin/Java, CLI) sobre
el estado de procesamiento ('Thinking') y la entrega de turnos.
"""

from __future__ import annotations
import json
import threading
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class EngineEventListener(Protocol):
    """Protocolo observador para clientes que consumen eventos del motor.
    
    Todas las cargas útiles se transmiten como cadenas JSON puras ('str') para
    garantizar el aislamiento total entre el motor y las capas de presentación
    (PySide6, Android Kotlin/Java, Web, CLI).
    """

    def on_thinking_changed(self, event_json: str) -> None:
        """Notifica cambio en el estado de procesamiento serializado en JSON (ThinkingEvent)."""
        ...

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        """Entrega el resultado del turno completado serializado en JSON (TurnResultProjection)."""
        ...

    def on_state_updated(self, ui_state_json: str) -> None:
        """Entrega el estado consolidado de la interfaz serializado en JSON (UIStateProjection)."""
        ...

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        """Notifica errores durante el procesamiento de una tarea."""
        ...


class BaseEngineEventListener:
    """Implementación base vacía del listener para conveniencia de subclases."""

    def on_thinking_changed(self, event_json: str) -> None:
        pass

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        pass

    def on_state_updated(self, ui_state_json: str) -> None:
        pass

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        pass


class SyncCollectingEventListener(BaseEngineEventListener):
    """Observador thread-safe que recolecta eventos en orden y permite esperas síncronas.

    Almacena las cargas útiles directamente como cadenas JSON.
    Especialmente útil para suites de pruebas unitarias, scripts y herramientas de diagnóstico.
    """

    def __init__(self) -> None:
        self.thinking_events: List[str] = []
        self.completed_tasks: List[Tuple[str, str]] = []
        self.state_updates: List[str] = []
        self.errors: List[Tuple[str, str, str]] = []
        self.task_completed_event = threading.Event()
        self.thinking_done_event = threading.Event()
        self.last_task_id: Optional[str] = None

    def on_thinking_changed(self, event_json: str) -> None:
        self.thinking_events.append(event_json)
        try:
            data = json.loads(event_json)
            if not data.get("is_thinking", False):
                self.thinking_done_event.set()
        except Exception:
            pass

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        self.completed_tasks.append((task_id, result_json))
        self.last_task_id = task_id
        self.task_completed_event.set()

    def on_state_updated(self, ui_state_json: str) -> None:
        self.state_updates.append(ui_state_json)

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        self.errors.append((task_id, error_message, error_code))

    def wait_for_completion(self, timeout: float = 3.0) -> bool:
        """Espera a que se complete una tarea y se apague el indicador thinking."""
        completed = self.task_completed_event.wait(timeout=timeout)
        thinking = self.thinking_done_event.wait(timeout=timeout)
        return completed and thinking

    def reset_events(self) -> None:
        """Limpia todos los eventos almacenados y reinicia las banderas de sincronización."""
        self.thinking_events.clear()
        self.completed_tasks.clear()
        self.state_updates.clear()
        self.errors.clear()
        self.task_completed_event.clear()
        self.thinking_done_event.clear()
