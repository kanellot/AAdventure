"""Submódulo engines.transformer: orquestación de inferencia LLM y adaptadores."""

from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.engine import TransformerEngine
from engines.transformer.factory import (
    BACKEND_LLAMA_CPP,
    BACKEND_LM_STUDIO,
    LLMFactory,
    create_llm_adapter,
)
from engines.transformer.llama_cpp_adapter import LlamaCppAdapter
from engines.transformer.lm_studio_adapter import LMStudioAdapter
from engines.transformer.schema_validator import SchemaValidator

__all__ = [
    "TransformerEngine",
    "BaseLLMAdapter",
    "LlamaCppAdapter",
    "LMStudioAdapter",
    "SchemaValidator",
    "LLMFactory",
    "create_llm_adapter",
    "BACKEND_LLAMA_CPP",
    "BACKEND_LM_STUDIO",
]
