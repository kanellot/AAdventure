"""Backend simulado de embeddings para testing y entornos ligeros."""

import math
import re
from typing import List, Set
from engines.embedding.base_backend import BaseEmbeddingBackend


class MockEmbeddingBackend(BaseEmbeddingBackend):
    """Backend simulado basado en coincidencia léxica y n-gramas sin dependencias externas."""

    STOPWORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "de", "del", "al", "a", "en", "por", "para", "con", "y", "o", "que",
    }

    def _normalize_tokens(self, text: str) -> Set[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        tokens = set()
        for w in words:
            if w in self.STOPWORDS:
                continue
            tokens.add(w)
            if len(w) >= 3:
                tokens.add(w[:3])
            if len(w) >= 4:
                tokens.add(w[:4])
            if len(w) >= 5:
                tokens.add(w[:5])
        return tokens

    def embed_text(self, text: str) -> Set[str]:
        """Devuelve el conjunto de tokens normalizados como vector simbólico."""
        return self._normalize_tokens(text)

    def embed_batch(self, texts: List[str]) -> List[Set[str]]:
        """Genera representaciones simbólicas para una lista de textos."""
        return [self.embed_text(t) for t in texts]

    def compute_similarity(self, vec_a: Set[str], vec_b: Set[str]) -> float:
        """Calcula la similitud entre los conjuntos de tokens."""
        if not vec_a or not vec_b:
            return 0.0

        intersection = vec_a.intersection(vec_b)
        if not intersection:
            return 0.0

        score = len(intersection) / math.sqrt(len(vec_a) * len(vec_b))
        scaled = min(1.0, score * 1.5)
        return round(scaled, 4)
