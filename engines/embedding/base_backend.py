"""Interfaz base para backends de embeddings semánticos."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple


class BaseEmbeddingBackend(ABC):
    """Clase base abstracta para backends de generación y comparación de embeddings."""

    @abstractmethod
    def embed_text(self, text: str) -> Any:
        """Genera el embedding para una sola cadena de texto."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> Any:
        """Genera embeddings para una lista de textos."""
        pass

    @abstractmethod
    def compute_similarity(self, vec_a: Any, vec_b: Any) -> float:
        """Calcula la similitud coseno entre dos vectores (entre 0.0 y 1.0)."""
        pass

    def compute_max_similarity(self, query: str, target_phrases: List[str]) -> Tuple[float, Optional[str]]:
        """Calcula la máxima similitud entre una consulta y una lista de frases objetivo."""
        if not target_phrases:
            return 0.0, None

        query_vec = self.embed_text(query)
        best_score = 0.0
        best_phrase = None

        for phrase in target_phrases:
            phrase_vec = self.embed_text(phrase)
            score = self.compute_similarity(query_vec, phrase_vec)
            if score > best_score:
                best_score = score
                best_phrase = phrase

        return best_score, best_phrase
