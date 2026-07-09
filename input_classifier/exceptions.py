class InputClassifierError(Exception):
    """Excepción base de todos los errores dentro de InputClassifier."""
    pass


class ModelGenerationError(InputClassifierError):
    """Lanzada cuando el modelo LLM falla al generar una respuesta."""
    pass


class OutputValidationError(InputClassifierError):
    """Lanzada cuando la respuesta generada por el LLM no cumple con el esquema esperado."""
    pass
