from transformer_engine.base_llm import BaseLLM
from transformer_engine.prompt_builder import PromptBuilder
from transformer_engine.validator import Validator

class DungeonMaster:
    """Orquestador genérico del motor narrativo que coordina prompts, inferencia y validación."""

    def __init__(self, llm_adapter: BaseLLM):
        """Inicializa el DungeonMaster inyectando el adaptador de LLM.

        Args:
            llm_adapter: Instancia que implementa la interfaz BaseLLM.
        """
        self.llm_adapter = llm_adapter

    def execute(
        self,
        rules_path: str,
        game_context_json: str,
        user_input: str,
        schema_path: str
    ) -> dict:
        """Construye el prompt, delega la generación al LLM, valida el JSON contra el esquema y retorna el resultado.

        Args:
            rules_path: Path al archivo Markdown de instrucciones de rol/reglas.
            game_context_json: Estado actual serializado como JSON para inyectar en el contexto.
            user_input: La entrada del jugador o acción a procesar.
            schema_path: Path al archivo JSON Schema para validar el resultado.

        Returns:
            dict: La respuesta estructurada y validada correctamente.
        """
        # 1. Construir el prompt
        prompt = PromptBuilder.build(rules_path, game_context_json, user_input)

        # 2. Generar respuesta usando el LLM
        raw_output = self.llm_adapter.generate(prompt)

        # 3. Validar estructuralmente contra el archivo de esquema JSON Schema
        Validator.validate_json(raw_output, schema_path)

        return raw_output
