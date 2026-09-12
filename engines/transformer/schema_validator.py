"""Validador de esquemas estructurados devueltos por los modelos."""

from typing import Type
from pydantic import BaseModel


class SchemaValidator:
    """Validador dinámico de JSON basado en modelos de dominio Pydantic."""

    @staticmethod
    def validate_json(data: dict, model: Type[BaseModel]) -> BaseModel:
        """Valida que un diccionario de datos cumpla con el modelo Pydantic."""
        return model.model_validate(data)
