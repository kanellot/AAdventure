"""Fábrica para instanciar backends de embeddings semánticos."""

import json
import logging
import os
from typing import Optional
from engines.embedding.base_backend import BaseEmbeddingBackend
from engines.embedding.mock_backend import MockEmbeddingBackend

logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """Fábrica para instanciar y obtener la implementación adecuada de embeddings."""

    _instance: Optional[BaseEmbeddingBackend] = None

    @classmethod
    def set_backend(cls, backend: BaseEmbeddingBackend) -> None:
        """Establece directamente una instancia de backend para pruebas o inyección de dependencias."""
        cls._instance = backend

    @classmethod
    def get_backend(
        cls,
        backend_type: Optional[str] = None,
        config_path: Optional[str] = None,
        force_new: bool = False,
    ) -> BaseEmbeddingBackend:
        """Obtiene o instancia el backend de embeddings configurado."""
        if cls._instance is not None and not force_new and backend_type is None:
            return cls._instance

        selected_backend = backend_type
        if not selected_backend and config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    conf = json.load(f)
                    selected_backend = conf.get("embedding_backend")
            except Exception:
                pass

        if not selected_backend:
            selected_backend = os.environ.get("EMBEDDING_BACKEND", "pytorch")

        selected_backend = selected_backend.lower().strip()

        backend: Optional[BaseEmbeddingBackend] = None

        if selected_backend in ["pytorch", "sentence_transformers", "torch"]:
            try:
                from engines.embedding.pytorch_backend import PyTorchEmbeddingBackend
                backend = PyTorchEmbeddingBackend()
            except ImportError as e:
                logger.warning(
                    f"No se pudo cargar el backend PyTorch ({e}). "
                    "Usando MockEmbeddingBackend como respaldo automático."
                )
                backend = MockEmbeddingBackend()
            except Exception as e:
                logger.warning(
                    f"Error al inicializar el backend PyTorch ({e}). "
                    "Usando MockEmbeddingBackend como respaldo automático."
                )
                backend = MockEmbeddingBackend()
        elif selected_backend == "mock":
            backend = MockEmbeddingBackend()
        else:
            logger.warning(f"Backend '{selected_backend}' desconocido. Usando MockEmbeddingBackend.")
            backend = MockEmbeddingBackend()

        if not force_new:
            cls._instance = backend

        return backend
