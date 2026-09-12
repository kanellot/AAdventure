"""Adaptador para interactuar con modelos locales GGUF mediante llama-cpp-python."""

import json
from typing import Optional
from engines.transformer.base_adapter import BaseLLMAdapter

try:
    import llama_cpp
except ImportError:
    llama_cpp = None


class LlamaCppAdapter(BaseLLMAdapter):
    """Adaptador que utiliza la librería llama-cpp-python para modelos locales GGUF."""

    def __init__(self, config_path: str):
        if llama_cpp is None:
            raise ImportError(
                "La librería 'llama-cpp-python' no está instalada en el entorno virtual.\n"
                "Para utilizar LlamaCppAdapter, instálala y descarga un modelo GGUF compatible."
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        llama_conf = self.config.get("llama_cpp", self.config)
        self.model_path = llama_conf.get("model_path", self.config.get("model_path"))
        self.llm_params = {
            "n_ctx": llama_conf.get("n_ctx", self.config.get("n_ctx", 2048)),
            "n_gpu_layers": llama_conf.get("n_gpu_layers", self.config.get("n_gpu_layers", 0)),
            "n_threads": llama_conf.get("n_threads", self.config.get("n_threads", 4)),
        }

        try:
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                verbose=False,
                **self.llm_params,
            )
        except Exception as e:
            raise RuntimeError(f"Error al cargar el modelo GGUF en '{self.model_path}': {e}")

    def generate(
        self,
        prompt: str,
        profile_name: str = "narrator",
        response_schema: Optional[dict] = None,
        schema_name: Optional[str] = None,
    ) -> dict:
        """Envía el prompt al modelo local configurando la salida para formato JSON."""
        if not hasattr(self, "llm") or self.llm is None:
            raise RuntimeError("El modelo Llama no ha sido inicializado correctamente.")

        profiles = self.config.get("inference_profiles", {})
        profile = profiles.get(profile_name, {})

        temperature = profile.get("temperature", self.config.get("temperature", 0.5))
        max_tokens = profile.get("max_tokens", self.config.get("max_tokens", 512))

        content_text = ""
        try:
            response = self.llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un motor de juego de rol estructurado. Tu salida debe ser estrictamente el objeto JSON solicitado, sin explicaciones, rodeos ni comentarios adicionales.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content_text = response["choices"][0]["message"]["content"]
            if not content_text:
                raise ValueError("El modelo retornó una respuesta de texto vacía.")

            cleaned_text = content_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            return json.loads(cleaned_text.strip())

        except json.JSONDecodeError as jde:
            raise ValueError(f"El modelo generó un texto que no es un JSON válido:\n{content_text}\nDetalle: {jde}")
        except Exception as e:
            raise RuntimeError(f"Ocurrió un error inesperado durante la inferencia con llama-cpp: {e}")
