from abc import ABC, abstractmethod

class BaseLLM(ABC):
    """Interfaz abstracta (DIP) para los adaptadores de LLM."""

    @abstractmethod
    def generate(self, prompt: str) -> dict:
        """Genera una respuesta estructurada (JSON) a partir de un prompt.

        Args:
            prompt: El texto completo con las instrucciones y el input del usuario.

        Returns:
            dict: La respuesta estructurada del modelo en formato de diccionario de Python.
        """
        pass
