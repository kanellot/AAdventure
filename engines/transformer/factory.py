"""Fábrica de adaptadores LLM para engines.transformer."""

import json
import os
from typing import Any, Dict, Union
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.llama_cpp_adapter import LlamaCppAdapter
from engines.transformer.lm_studio_adapter import LMStudioAdapter

BACKEND_LLAMA_CPP = "llama_cpp"
BACKEND_LM_STUDIO = "lm_studio"


class LLMFactory:
    """Fábrica para instanciar el adaptador de LLM configurado."""

    @classmethod
    def create_adapter(
        cls,
        config_or_path: Union[str, Dict[str, Any]] = "Resources/system_data/llm_config.json",
    ) -> BaseLLMAdapter:
        """Crea e inicializa una instancia del adaptador LLM configurado."""
        if isinstance(config_or_path, str):
            if not os.path.exists(config_or_path):
                raise FileNotFoundError(f"No se encontró el archivo de configuración del LLM en '{config_or_path}'.")
            with open(config_or_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            config_path = config_or_path
        elif isinstance(config_or_path, dict):
            config_data = config_or_path
            config_path = None
        else:
            raise ValueError(f"Parámetro de configuración inválido: {type(config_or_path)}")

        backend = config_data.get("active_backend", config_data.get("backend", BACKEND_LM_STUDIO))
        backend_normalized = str(backend).strip().lower().replace("-", "_")

        if backend_normalized in [BACKEND_LM_STUDIO, "lmstudio", "openai"]:
            return LMStudioAdapter(config_data)

        if backend_normalized in [BACKEND_LLAMA_CPP, "llamacpp"]:
            if config_path is None:
                raise ValueError("LlamaCppAdapter requiere una ruta de archivo de configuración válida.")
            return LlamaCppAdapter(config_path=config_path)

        raise ValueError(
            f"Backend de LLM desconocido: '{backend}'. "
            f"Opciones válidas: '{BACKEND_LM_STUDIO}', '{BACKEND_LLAMA_CPP}'"
        )


def create_llm_adapter(
    config_or_path: Union[str, Dict[str, Any]] = "Resources/system_data/llm_config.json",
) -> BaseLLMAdapter:
    """Función de conveniencia para instanciar el adaptador LLM."""
    return LLMFactory.create_adapter(config_or_path)
