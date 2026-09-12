"""Motor orquestador de inferencia LLM y validación estructurada."""

import sys
from typing import Optional, Type
from pydantic import BaseModel
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.schema_validator import SchemaValidator


class TransformerEngine:
    """Fachada y orquestador del motor de inferencia LLM."""

    def __init__(self, llm_adapter: BaseLLMAdapter):
        self.llm_adapter = llm_adapter
        self.last_prompt = None
        self.last_raw_output = None

    def execute(
        self,
        prompt: str,
        response_schema: Optional[dict] = None,
        response_model: Optional[Type[BaseModel]] = None,
        profile_name: str = "narrator",
        schema_name: Optional[str] = None,
    ) -> dict:
        """Delega la generación del prompt al LLM y valida la salida estructurada."""
        self.last_prompt = prompt

        if schema_name is None and response_model:
            schema_name = getattr(response_model, "__name__", "StructuredResponse")

        main_mod = sys.modules.get("__main__")
        if getattr(main_mod, "DEBUG_PROMPS", 0) or getattr(main_mod, "DEBUG_PROMPTS", 0):
            print("\n" + "=" * 65)
            print("DEBUG: PROMPT ENVIADO AL MODELO")
            print("=" * 65)
            print(prompt)
            print("=" * 65 + "\n")

        raw_output = self.llm_adapter.generate(
            prompt,
            profile_name=profile_name,
            response_schema=response_schema,
            schema_name=schema_name,
        )
        self.last_raw_output = raw_output

        if getattr(main_mod, "DEBUG_RESPONSE", 0):
            print("\n" + "=" * 65)
            print(f"DEBUG: RESPUESTA LLM RECIBIDA (profile={profile_name})")
            print("=" * 65)
            print(raw_output)
            print("=" * 65 + "\n")

        if response_model:
            validated_instance = SchemaValidator.validate_json(raw_output, response_model)
            return validated_instance.model_dump()

        if isinstance(raw_output, dict):
            return raw_output
        return {"msg": str(raw_output)}
