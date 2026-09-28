"""Gestor de concurrencia, cola de tareas en segundo plano y observadores."""

from __future__ import annotations
import logging
import queue
import threading
from typing import Callable, List, Optional
from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import EngineEventListener, EngineTask, ThinkingEvent

logger = logging.getLogger(__name__)


class EngineWorker:
    """Administra el ciclo de vida del hilo secundario, la cola de tareas y los observadores."""

    def __init__(
        self,
        turn_executor: Callable[[EngineTask], TurnResultProjection],
        ui_state_provider: Callable[[], UIStateProjection],
        listeners: Optional[List[EngineEventListener]] = None,
    ):
        self.turn_executor = turn_executor
        self.ui_state_provider = ui_state_provider
        self.listeners: List[EngineEventListener] = list(listeners or [])
        self.task_queue: queue.Queue[EngineTask] = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self.lock = threading.RLock()

    def start(self) -> None:
        """Inicia el worker en segundo plano."""
        with self.lock:
            if self._running:
                return
            self._running = True
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                name="GameEngineWorker",
                daemon=True,
            )
            self.worker_thread.start()

    def stop(self) -> None:
        """Detiene el hilo de trabajo de forma ordenada con centinela."""
        with self.lock:
            self._running = False
        self.task_queue.put(EngineTask(task_id="__STOP__", action=""))
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)

    def add_listener(self, listener: EngineEventListener) -> None:
        """Registra un observador."""
        with self.lock:
            if listener not in self.listeners:
                self.listeners.append(listener)

    def remove_listener(self, listener: EngineEventListener) -> None:
        """Elimina un observador."""
        with self.lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def notify_thinking(
        self,
        is_thinking: bool,
        task_id: str = "",
        action: str = "",
        target: str = "",
        source: str = "PLAYER",
    ) -> None:
        """Notifica el estado de pensamiento a la interfaz."""
        msg = f"Pensando... [{action} -> {target}]" if action else "Pensando respuesta..."
        event = ThinkingEvent(
            task_id=task_id,
            is_thinking=is_thinking,
            action=action,
            target=target,
            source=source if source in ("PLAYER", "LORE") else "PLAYER",
            message=msg if is_thinking else "",
        )
        event_json = event.model_dump_json()
        with self.lock:
            active_listeners = list(self.listeners)
        for l in active_listeners:
            if hasattr(l, "on_thinking_changed"):
                l.on_thinking_changed(event_json)

    def notify_turn_completed(self, turn_result: TurnResultProjection, task_id: str = "") -> None:
        """Emite la proyección consolidada a los observadores registrados."""
        result_json = turn_result.model_dump_json()
        ui_state_json = self.ui_state_provider().model_dump_json()
        with self.lock:
            active_listeners = list(self.listeners)
        for l in active_listeners:
            if hasattr(l, "on_turn_completed"):
                l.on_turn_completed(turn_result)
            if hasattr(l, "on_task_completed"):
                l.on_task_completed(task_id, result_json)
            if hasattr(l, "on_state_updated"):
                l.on_state_updated(ui_state_json)

    def _worker_loop(self) -> None:
        """Bucle consumidor de la cola de tareas en segundo plano."""
        while self._running:
            try:
                task = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if task.task_id == "__STOP__":
                self.task_queue.task_done()
                break

            try:
                self.notify_thinking(
                    is_thinking=True,
                    task_id=task.task_id,
                    action=task.action,
                    target=task.target,
                    source=task.source,
                )
                with self.lock:
                    result = self.turn_executor(task)
                self.notify_turn_completed(result, task_id=task.task_id)
            except Exception as e:
                logger.error("Error al procesar tarea %s: %s", task.task_id, e, exc_info=True)
                with self.lock:
                    active_listeners = list(self.listeners)
                for l in active_listeners:
                    if hasattr(l, "on_error"):
                        l.on_error(task.task_id, str(e), "ENGINE_ERROR")
            finally:
                self.notify_thinking(
                    is_thinking=False,
                    task_id=task.task_id,
                    action=task.action,
                    target=task.target,
                    source=task.source,
                )
                self.task_queue.task_done()
