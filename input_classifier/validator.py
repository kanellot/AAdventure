from pydantic import ValidationError
from .models import InputActions
from .exceptions import OutputValidationError


class OutputValidator:
    """Clase responsable de validar estructuralmente la respuesta obtenida del LLM."""

    def validate(self, raw_output: dict) -> InputActions:
        """Valida que un diccionario cumpla exactamente con el esquema de InputAction (el formato {"actions": [...]}).

        Args:
            raw_output: Diccionario obtenido del LLMAdapter.

        Returns:
            InputActions: Objeto InputAction validado estructuralmente.

        Raises:
            OutputValidationError: Si el formato es incorrecto, faltan campos requeridos o hay tipos inválidos.
        """
        if not isinstance(raw_output, dict):
            raise OutputValidationError(
                f"La salida del adaptador del modelo no es un diccionario Python. "
                f"Tipo recibido: {type(raw_output).__name__}"
            )

        try:
            # Validación directa del formato {"actions": [ActionDetail, ...]}
            return InputActions(**raw_output)
        except ValidationError as ve:
            raise OutputValidationError(
                f"La respuesta estructurada del modelo no coincide con el esquema InputAction esperado.\n"
                f"Detalles de validación de Pydantic:\n{ve}"
            )
