import os
import json
from jsonschema import validate, ValidationError


class Validator:
    """Validador dinámico de JSON basado en la especificación JSON Schema."""

    @staticmethod
    def validate_json(data: dict, schema_path: str):
        """Valida que un diccionario de datos 'data' cumpla con el esquema JSON Schema.

        Args:
            data: Diccionario de datos devuelto por el LLM.
            schema_path: Ruta al archivo .json que define el esquema JSON Schema de validación.

        Raises:
            FileNotFoundError: Si el archivo de esquema no existe.
            ValidationError: Si la estructura de 'data' no pasa la validación del esquema.
        """
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"No se encontró el archivo de esquema JSON en '{schema_path}'.")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validación nativa contra el esquema JSON Schema
        validate(instance=data, schema=schema)
