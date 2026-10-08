"""Backend de embeddings semánticos basado en PyTorch y sentence-transformers."""

import logging
import sys
from typing import Any, List, Optional

try:
    # Optimización para PySide6/Shiboken: evitar que tokenize todos los submódulos de ML en disco
    if "shibokensupport.feature" in sys.modules:
        sf = sys.modules["shibokensupport.feature"]
        orig_uses = getattr(sf, "_mod_uses_pyside", None)
        if orig_uses and not getattr(sf, "_mod_uses_pyside_fast", False):
            def _fast_uses(m):
                n = getattr(m, "__name__", "")
                if n.startswith(("torch", "transformers", "sentence_transformers", "scipy", "sklearn", "numpy",
                                 "huggingface_hub", "timm", "tokenizers", "safetensors", "accelerate")):
                    return False
                return orig_uses(m)

            sf._mod_uses_pyside = _fast_uses
            sf._mod_uses_pyside_fast = True

    import torch
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    torch = None
    SentenceTransformer = None
    util = None

from engines.embedding.base_backend import BaseEmbeddingBackend

logger = logging.getLogger(__name__)


class PyTorchEmbeddingBackend(BaseEmbeddingBackend):
    """Backend de embeddings de alta precisión basado en PyTorch y sentence-transformers."""

    def __init__(
            self,
            model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
            device: Optional[str] = None,
    ):
        if torch is None or SentenceTransformer is None or util is None:
            raise ImportError(
                "Para utilizar PyTorchEmbeddingBackend debes tener instalado 'sentence-transformers' y 'torch'."
            )

        self.torch = torch
        self.util = util
        self.device = device or ("cuda" if self.torch.cuda.is_available() else "cpu")
        try:
            self.model = SentenceTransformer(model_name, device=self.device, local_files_only=True)
        except Exception:
            logger.info("Cargando modelo de embeddings semánticos '%s' en [%s]...", model_name, self.device)
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
