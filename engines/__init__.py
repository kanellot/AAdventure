"""Paquete principal de motores de ejecución de AAdventure.

Expone exclusivamente la fachada pública AdventureSession para clientes y frontends externos,
así como el protocolo de observadores (EngineEventListener) y DTOs reactivos.
Los subsistemas internos (GameEngine, TransformerEngine, EmbeddingFactory, LoreRouter, etc.)
quedan encapsulados como detalles de implementación.
"""

from engines.session import AdventureSession
from engines.events import ThinkingEvent, EngineTask
from engines.listeners import (
    EngineEventListener,
    BaseEngineEventListener,
    SyncCollectingEventListener,
)

__all__ = [
    "AdventureSession",
    "EngineEventListener",
    "BaseEngineEventListener",
    "SyncCollectingEventListener",
    "ThinkingEvent",
    "EngineTask",
]
