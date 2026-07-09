import json
from abc import ABC, abstractmethod
from typing import Any
from .exceptions import ModelGenerationError

# Intentamos importar llama_cpp para que no falle el parseo si no está instalado aún
try:
    import llama_cpp
except ImportError:
    llama_cpp = None

# Constante de placeholder para la ruta del modelo GGUF
DEFAULT_MODEL_PATH = "C:\\Users\\kanel\\.lmstudio\\models\\lmstudio-community\\gemma-3-4b-it-GGUF\\gemma-3-4b-it-Q4_K_M.gguf"

# Configuración por defecto para el modelo local (placeholder)
DEFAULT_MODEL_CONFIG = {
    "n_ctx": 2048,          # Tamaño del contexto de tokens
    "n_gpu_layers": 0,      # Número de capas a mover a GPU (0 = solo CPU)
    "n_threads": 4,         # Hilos de ejecución CPU
    "temperature": 0.1,     # Creatividad baja para obtener respuestas consistentes
    "max_tokens": 512,      # Máximo de tokens en la respuesta
}


class BaseLLM(ABC):
    """Interfaz abstracta (DIP) para los adaptadores de LLM."""

    @abstractmethod
    def generate(self, prompt: str) -> dict:
        """Genera una respuesta estructurada (JSON) a partir de un prompt.

        Args:
            prompt: El texto formateado con las instrucciones del sistema y entrada del usuario.

        Returns:
            dict: La respuesta estructurada del modelo en formato de diccionario de Python.

        Raises:
            ModelGenerationError: Si ocurre un fallo en la inicialización o inferencia del LLM.
        """
        pass


class LlamaCppAdapter(BaseLLM):
    """Implementación de BaseLLM utilizando la librería llama-cpp-python para modelos locales GGUF."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, config: dict[str, Any] = None):
        """Inicializa el cargador de llama-cpp-python con el path del modelo y su configuración.

        Args:
            model_path: Path absoluto o relativo al archivo .gguf del modelo.
            config: Opciones de configuración del modelo y generación.
        """
        if llama_cpp is None:
            raise ModelGenerationError(
                "La librería 'llama-cpp-python' no está instalada en el entorno virtual.\n"
                "Para poder utilizar el LlamaCppAdapter, por favor instálala "
                "y descarga un modelo GGUF compatible."
            )

        self.model_path = model_path
        self.config = config or DEFAULT_MODEL_CONFIG.copy()

        # Separamos parámetros de carga de modelo de los parámetros de inferencia
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
            raise ModelGenerationError(
                f"Error crítico al intentar cargar el archivo del modelo GGUF en '{self.model_path}': {e}"
            )

    def generate(self, prompt: str) -> dict:
        """Envía el prompt al modelo local configurando la salida para formato JSON.

        Args:
            prompt: El texto completo del prompt.

        Returns:
            dict: El JSON generado y parseado como diccionario.

        Raises:
            ModelGenerationError: Si el modelo no está cargado o la inferencia/parseo falla.
        """
        if not hasattr(self, "llm") or self.llm is None:
            raise ModelGenerationError("El modelo Llama no ha sido inicializado correctamente.")

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
                raise ModelGenerationError("El modelo retornó una respuesta de texto vacía.")

            # Parseamos el JSON a diccionario
            return json.loads(content_text)

        except json.JSONDecodeError as jde:
            raise ModelGenerationError(
                f"El modelo generó un texto que no es un JSON válido:\n{content_text}\nDetalle: {jde}"
            )
        except Exception as e:
            raise ModelGenerationError(
                f"Ocurrió un error inesperado durante la inferencia con llama-cpp: {e}"
            )
