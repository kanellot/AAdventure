"""Adaptador simulado (Mock) de LLM para testing y ejecución desacoplada sin dependencias externas."""

from typing import Optional
from engines.transformer.base_adapter import BaseLLMAdapter


class MockLLMAdapter(BaseLLMAdapter):
    """Adaptador de pruebas que genera respuestas narrativas deterministas válidas para esquemas del motor."""

    def __init__(self, default_response: Optional[dict] = None):
        self.default_response = default_response
        self.last_prompt: Optional[str] = None
        self.call_count: int = 0

    def generate(
        self,
        prompt: str,
        profile_name: str = "narrator",
        response_schema: Optional[dict] = None,
        schema_name: Optional[str] = None,
    ) -> dict:
        self.last_prompt = prompt
        self.call_count += 1

        res = dict(self.default_response) if self.default_response is not None else {}

        # Respuestas por defecto válidas según el tipo de perfil o esquema
        p_name = (profile_name or "").lower()
        s_name = (schema_name or "").lower()

        if "move" in p_name or "move" in s_name:
            default_vals = {
                "msg": "Avanzas con precaución por el camino hasta llegar a tu destino.",
                "confidence": 1.0,
            }
        elif "look" in p_name or "look" in s_name:
            default_vals = {
                "msg": "Observas detenidamente los alrededores. Todo parece en calma.",
                "confidence": 1.0,
            }
        elif "dialogue" in p_name or "dialogue" in s_name or "talk" in p_name:
            default_vals = {
                "msg": "El personaje te mira y asiente con educación.",
                "affinity": 0.5,
                "confidence": 1.0,
            }
        else:
            default_vals = {"msg": "El turno se resuelve sin incidentes.", "confidence": 1.0}

        for k, v in default_vals.items():
            if k not in res:
                res[k] = v

        return res

