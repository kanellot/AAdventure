"""Motor fachada para generación y comparación de embeddings semánticos."""

from typing import Any, List, Optional, Tuple
from engines.embedding.base_backend import BaseEmbeddingBackend
from engines.embedding.factory import EmbeddingFactory


class EmbeddingEngine:
    """Fachada unificada para el motor de generación y comparación de embeddings."""

    def __init__(
        self,
        backend: Optional[BaseEmbeddingBackend] = None,
        config_path: Optional[str] = None,
        backend_type: Optional[str] = None,
    ):
        if backend is not None:
            self._backend = backend
        else:
            self._backend = EmbeddingFactory.get_backend(
                backend_type=backend_type,
                config_path=config_path,
            )

    @property
    def backend(self) -> BaseEmbeddingBackend:
        """Retorna la instancia del backend subyacente."""
        return self._backend

    def embed_text(self, text: str) -> Any:
        """Genera el embedding para una sola cadena de texto."""
        return self._backend.embed_text(text)

    def embed_batch(self, texts: List[str]) -> Any:
        """Genera embeddings para una lista de textos."""
        return self._backend.embed_batch(texts)

    def compute_similarity(self, vec_a: Any, vec_b: Any) -> float:
        """Calcula la similitud coseno entre dos vectores (entre 0.0 y 1.0)."""
        return self._backend.compute_similarity(vec_a, vec_b)

    def compute_max_similarity(self, query: str, target_phrases: List[str]) -> Tuple[float, Optional[str]]:
        """Calcula la máxima similitud entre una consulta y una lista de frases objetivo."""
        return self._backend.compute_max_similarity(query, target_phrases)
