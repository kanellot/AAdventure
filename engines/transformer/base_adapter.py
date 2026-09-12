"""Interfaz base para adaptadores de modelos de lenguaje (LLM)."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMAdapter(ABC):
    """Interfaz abstracta para los adaptadores de LLM."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        profile_name: str = "narrator",
        response_schema: Optional[dict] = None,
        schema_name: Optional[str] = None,
    ) -> dict:
        """Genera una respuesta estructurada (JSON) a partir de un prompt."""
        pass
