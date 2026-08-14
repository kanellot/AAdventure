from typing import Type
from pydantic import BaseModel, ValidationError


class Validator:
    """Validador dinámico de JSON basado en modelos de dominio Pydantic."""

    @staticmethod
    def validate_json(data: dict, model: Type[BaseModel]) -> BaseModel:
        """Valida que un diccionario de datos 'data' cumpla con el modelo Pydantic.

        Args:
            data: Diccionario de datos devuelto por el LLM.
            model: La clase del modelo Pydantic (dominio) contra la cual validar.

        Returns:
            BaseModel: La instancia validada y tipada del modelo.

        Raises:
            ValidationError: Si la estructura de 'data' no pasa la validación del modelo.
        """
        return model.model_validate(data)
