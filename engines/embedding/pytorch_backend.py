"""Backend de embeddings semánticos basado en PyTorch y sentence-transformers."""

from typing import Any, List, Optional
from engines.embedding.base_backend import BaseEmbeddingBackend


class PyTorchEmbeddingBackend(BaseEmbeddingBackend):
    """Backend de embeddings de alta precisión basado en PyTorch y sentence-transformers."""

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: Optional[str] = None,
    ):
        try:
            import torch
            from sentence_transformers import SentenceTransformer, util
            self.torch = torch
            self.util = util
        except ImportError as e:
            raise ImportError(
                "Para utilizar PyTorchEmbeddingBackend debes tener instalado 'sentence-transformers' y 'torch'.\n"
                f"Error original: {e}"
            )

        self.device = device or ("cuda" if self.torch.cuda.is_available() else "cpu")
        try:
            self.model = SentenceTransformer(model_name, device=self.device, local_files_only=True)
        except Exception:
            self.model = SentenceTransformer(model_name, device=self.device)

    def embed_text(self, text: str) -> Any:
        """Genera tensor normalizado para un texto."""
        return self.model.encode(text, convert_to_tensor=True, normalize_embeddings=True)

    def embed_batch(self, texts: List[str]) -> Any:
        """Genera tensores normalizados para un lote de textos."""
        if not texts:
            return []
        return self.model.encode(texts, convert_to_tensor=True, normalize_embeddings=True)

    def compute_similarity(self, vec_a: Any, vec_b: Any) -> float:
        """Calcula la similitud coseno entre dos vectores tensoriales."""
        sim = self.util.cos_sim(vec_a, vec_b)
        return float(sim.item())
