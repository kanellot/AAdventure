from typing import Type
from pydantic import BaseModel
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
        gamecontext: BaseModel,
        player_input: str,
        response_model: Type[BaseModel]
    ) -> dict:
        """Construye el prompt, delega la generación al LLM, valida el JSON contra el modelo de dominio y retorna el resultado.

        Args:
            rules_path: Path al archivo Markdown de instrucciones de rol/reglas.
            gamecontext: Objeto de dominio Pydantic que contiene el contexto.
            player_input: La entrada del jugador o acción a procesar.
            response_model: Clase del modelo Pydantic para validar el resultado.

        Returns:
            dict: La respuesta estructurada y validada correctamente como diccionario.
        """
        # Serializar el modelo de dominio a JSON string
        game_context_json = gamecontext.model_dump_json(indent=2)

        # 1. Construir el prompt
        prompt = PromptBuilder.build(rules_path, game_context_json, player_input)

        # 2. Generar respuesta usando el LLM
        raw_output = self.llm_adapter.generate(prompt)

        # 3. Validar estructuralmente contra el modelo de dominio (Pydantic)
        validated_instance = Validator.validate_json(raw_output, response_model)

        return validated_instance.model_dump()
