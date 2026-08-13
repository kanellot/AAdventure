import json
from typing import Any
from transformer_engine.base_llm import BaseLLM

# Intentamos importar llama_cpp para que no falle el parseo si no está instalado aún
try:
    import llama_cpp
except ImportError:
    llama_cpp = None


class TransformerModel(BaseLLM):
    """Implementación de BaseLLM utilizando la librería llama-cpp-python para modelos locales GGUF."""

    def __init__(self, config_path: str):
        """Inicializa el cargador de llama-cpp-python leyendo su configuración desde config_path.

        Args:
            config_path: Path al archivo llm_config.json de configuración del LLM.
        """
        if llama_cpp is None:
            raise ImportError(
                "La librería 'llama-cpp-python' no está instalada en el entorno virtual.\n"
                "Para poder utilizar el TransformerModel, por favor instálala "
                "y descarga un modelo GGUF compatible."
            )

        # Cargar configuración desde el JSON
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.model_path = self.config.get("model_path")
        self.llm_params = {
            "n_ctx": self.config.get("n_ctx", 2048),
            "n_gpu_layers": self.config.get("n_gpu_layers", 0),
            "n_threads": self.config.get("n_threads", 4),
        }

        try:
            # Inicializamos el modelo en modo no verboso para evitar logs masivos en consola
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                verbose=False,
                **self.llm_params
            )
        except Exception as e:
            raise RuntimeError(
                f"Error crítico al intentar cargar el archivo del modelo GGUF en '{self.model_path}': {e}"
            )

    def generate(self, prompt: str) -> dict:
        """Envía el prompt al modelo local configurando la salida para formato JSON.

        Args:
            prompt: El texto completo del prompt.

        Returns:
            dict: El JSON generado y parseado como diccionario.
        """
        if not hasattr(self, "llm") or self.llm is None:
            raise RuntimeError("El modelo Llama no ha sido inicializado correctamente.")

        temperature = self.config.get("temperature", 0.1)
        max_tokens = self.config.get("max_tokens", 512)

        try:
            # Solicita la inferencia forzando un formato JSON estructurado
            response = self.llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_object"
                },
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extraemos el contenido textual del mensaje de respuesta
            content_text = response["choices"][0]["message"]["content"]
            if not content_text:
                raise ValueError("El modelo retornó una respuesta de texto vacía.")

            # Parseamos el JSON a diccionario
            return json.loads(content_text)

        except json.JSONDecodeError as jde:
            raise ValueError(
                f"El modelo generó un texto que no es un JSON válido:\n{content_text}\nDetalle: {jde}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Ocurrió un error inesperado durante la inferencia con llama-cpp: {e}"
            )
