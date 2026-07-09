from .models import ClassificationContext, InputActions
from .llm_adapter import BaseLLM
from .prompt_builder import PromptBuilder
from .validator import OutputValidator


class InputClassifier:
    """Fachada pública del módulo InputClassifier.

    Orquesta todo el flujo de clasificación semántica, encargándose de solicitar la construcción
    del prompt, delegar la generación al LLM y validar la salida resultante con el esquema de negocio.
    """

    def __init__(
        self,
        llm_adapter: BaseLLM,
        prompt_builder: PromptBuilder = None,
        validator: OutputValidator = None
    ):
        """Inicializa el clasificador inyectando sus dependencias.

        Args:
            llm_adapter: Instancia concreta del adaptador que implementa BaseLLM.
            prompt_builder: Constructor de prompts personalizado. Si es None, crea uno por defecto.
            validator: Validador de salida estructurada. Si es None, crea uno por defecto.
        """
        self.llm_adapter = llm_adapter
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or OutputValidator()

    def classify(self, player_input: str, context: ClassificationContext) -> InputActions:
        """Clasifica semánticamente la entrada de texto del jugador en base al contexto.

        Args:
            player_input: Texto libre ingresado por el jugador.
            context: Contexto mínimo necesario para resolución semántica y de entidades.

        Returns:
            InputActions: Objeto con la acción, entidades, contenido y atributos identificados.

        Raises:
            InputClassifierError: Base para errores en el prompt, generación del LLM o validación.
        """
        # 1. Construimos el prompt integrando la plantilla, el contexto y el mensaje de entrada
        prompt = self.prompt_builder.build(player_input, context)

        # 2. Generamos la inferencia estructurada usando el LLM
        raw_output = self.llm_adapter.generate(prompt)

        # 3. Validamos que la salida tenga el esquema correcto y la convertimos en InputAction
        validated_action = self.validator.validate(raw_output)

        return validated_action
