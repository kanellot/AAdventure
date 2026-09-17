"""Paquete principal de motores de ejecución de AAdventure.

Expone exclusivamente la fachada pública AdventureSession para clientes y frontends externos.
Los subsistemas internos (GameEngine, TransformerEngine, EmbeddingFactory, LoreRouter, etc.)
quedan encapsulados como detalles de implementación.
"""

from engines.session import AdventureSession

__all__ = ["AdventureSession"]

