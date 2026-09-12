"""Submódulo engines.embedding: generación y evaluación de embeddings semánticos."""

from engines.embedding.base_backend import BaseEmbeddingBackend
from engines.embedding.engine import EmbeddingEngine
from engines.embedding.factory import EmbeddingFactory
from engines.embedding.mock_backend import MockEmbeddingBackend

__all__ = [
    "EmbeddingEngine",
    "BaseEmbeddingBackend",
    "MockEmbeddingBackend",
    "EmbeddingFactory",
]
