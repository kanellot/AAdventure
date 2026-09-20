"""DTOs de eventos para la comunicación reactiva Motor-UI.

Define los modelos de datos transferibles para desacoplar el bucle de ejecución
del motor y notificar a los clientes sobre el estado de procesamiento ('Thinking')
y las tareas en cola.
"""

from __future__ import annotations
import time
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

from domains.projections import TurnResultProjection, UIStateProjection


class ThinkingEvent(BaseModel):
    """Evento emitido al cambiar el estado de procesamiento de una tarea.

    Alimentará spinners e indicadores visuales de carga en la UI.
    """

    task_id: str
    is_thinking: bool
    action: str = ""
    target: str = ""
    source: Literal["PLAYER", "LORE"] = "PLAYER"
    message: str = "Pensando..."


class EngineTask(BaseModel):
    """Tarea individual encolada para ejecución en el motor."""

    task_id: str
    action: str = ""
    target: str = ""
    player_input: str = ""
    source: Literal["PLAYER", "LORE"] = "PLAYER"
    created_at: float = Field(default_factory=time.time)


# Re-exportación de listeners desde engines.listeners para compatibilidad
from engines.listeners import (  # noqa: E402
    EngineEventListener,
    BaseEngineEventListener,
    SyncCollectingEventListener,
)

__all__ = [
    "ThinkingEvent",
    "EngineTask",
    "EngineEventListener",
    "BaseEngineEventListener",
    "SyncCollectingEventListener",
]
