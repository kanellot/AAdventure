"""Pruebas unitarias para el motor transformer, adaptadores y validación de esquemas."""

import unittest
from typing import Optional
from pydantic import BaseModel, Field, ValidationError
from engines.transformer import SchemaValidator, TransformerEngine, LLMFactory
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.lm_studio_adapter import LMStudioAdapter


class SampleResponseModel(BaseModel):
    msg: str = Field(..., description="Mensaje narrativo")
    confidence: float = Field(default=1.0)


class MockLLMAdapter(BaseLLMAdapter):
    """Adaptador de pruebas que devuelve una respuesta predefinida."""

    def __init__(self, response_payload: dict):
        self.payload = response_payload
        self.last_prompt = None

    def generate(
        self,
        prompt: str,
        profile_name: str = "narrator",
        response_schema: Optional[dict] = None,
        schema_name: Optional[str] = None,
    ) -> dict:
        self.last_prompt = prompt
        return self.payload


class TestTransformerEngine(unittest.TestCase):
    """Verifica la orquestación de inferencia y la validación de esquemas JSON."""

    def test_schema_validator_success(self):
        data = {"msg": "Hola aventurero", "confidence": 0.95}
        model_inst = SchemaValidator.validate_json(data, SampleResponseModel)
        self.assertIsInstance(model_inst, SampleResponseModel)
        self.assertEqual(model_inst.msg, "Hola aventurero")

    def test_schema_validator_failure(self):
        invalid_data = {"confidence": "not_a_number"}
        with self.assertRaises(ValidationError):
            SchemaValidator.validate_json(invalid_data, SampleResponseModel)

    def test_transformer_engine_execution(self):
        mock_adapter = MockLLMAdapter({"msg": "Respuesta simulada", "confidence": 0.8})
        engine = TransformerEngine(mock_adapter)

        result = engine.execute(
            prompt="Describe la sala",
            response_model=SampleResponseModel,
            profile_name="narrator",
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(result["msg"], "Respuesta simulada")
        self.assertEqual(result["confidence"], 0.8)
        self.assertEqual(engine.last_prompt, "Describe la sala")

    def test_llm_factory_creation(self):
        cfg = {"backend": "lm_studio", "api_url": "http://localhost:1234"}
        adapter = LLMFactory.create_adapter(cfg)
        self.assertIsInstance(adapter, LMStudioAdapter)

    def test_llm_factory_invalid_backend(self):
        cfg = {"backend": "unknown_backend"}
        with self.assertRaises(ValueError):
            LLMFactory.create_adapter(cfg)


if __name__ == "__main__":
    unittest.main()
