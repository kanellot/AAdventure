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
        response_model: Type[BaseModel],
        profile_name: str = "narrator"
    ) -> dict:
        """Construye el prompt, delega la generación al LLM, valida el JSON contra el modelo de dominio y retorna el resultado.

        Args:
            rules_path: Path al archivo Markdown de instrucciones de rol/reglas.
            gamecontext: Objeto de dominio Pydantic que contiene el contexto.
            player_input: La entrada del jugador o acción a procesar.
            response_model: Clase del modelo Pydantic para validar el resultado.
            profile_name: El nombre del perfil de inferencia a utilizar en el LLM.

        Returns:
            dict: La respuesta estructurada y validada correctamente como diccionario.
        """
        # 1. Obtener la representación de contexto (preferiblemente Markdown)
        if hasattr(gamecontext, "to_markdown") and callable(getattr(gamecontext, "to_markdown")):
            game_context_str = gamecontext.to_markdown()
        else:
            game_context_str = gamecontext.model_dump_json(indent=2)

        # 2. Construir el prompt
        prompt = PromptBuilder.build(rules_path, gamecontext, game_context_str, player_input)

        # DEBUG: Imprimir el prompt completo antes de enviarlo al modelo
        print("\n" + "=" * 65)
        print(f"DEBUG: PROMPT ENVIADO AL MODELO ({rules_path})")
        print("=" * 65)
        print(prompt)
        print("=" * 65 + "\n")

        # 3. Generar respuesta usando el LLM
        raw_output = self.llm_adapter.generate(prompt, profile_name=profile_name)

        # 3. Validar estructuralmente contra el modelo de dominio (Pydantic)
        validated_instance = Validator.validate_json(raw_output, response_model)

        return validated_instance.model_dump()
