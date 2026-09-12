"""Clase base y plantilla de ejecución para las acciones (steps) del juego."""

from abc import ABC, abstractmethod
from typing import Dict, Generic, Optional, Tuple, Type, TypeVar
from domains import ContextType, ResponseType, ResultType
from engines.game.prompt_builder import PromptBuilder
from engines.game.state_controller import GameStateController

C = TypeVar("C", bound=ContextType)
R = TypeVar("R", bound=ResponseType)


class BaseAction(ABC, Generic[C, R]):
    """Interfaz base (template method) para las acciones del juego."""

    @property
    @abstractmethod
    def rules_path(self) -> str:
        """Ruta al archivo Markdown que define las reglas de rol para el LLM."""
        pass

    @property
    @abstractmethod
    def response_model(self) -> Type[R]:
        """Clase del modelo Pydantic para validar la respuesta estructurada del LLM."""
        pass

    @property
    def profile_name(self) -> str:
        """Nombre del perfil de inferencia del LLM."""
        return "narrator"

    def build_context(
        self,
        game_state_controller: GameStateController,
        player_input: str,
    ) -> C:
        """Construye y retorna el modelo de contexto para el LLM."""
        raise NotImplementedError

    def get_template_tags(self, ctx: C) -> Dict[str, str]:
        """Genera tags runtime para inyectar en la plantilla del prompt."""
        return {}

    def to_markdown(self, ctx: C) -> str:
        """Genera la representación alternativa del contexto en formato Markdown."""
        return ""

    def build_prompt(self, ctx: C, player_input: str) -> str:
        """Construye el prompt completo utilizando PromptBuilder y la configuración del step."""
        tags = self.get_template_tags(ctx)
        ctx_md = self.to_markdown(ctx)
        return PromptBuilder.build(
            rules_path=self.rules_path,
            gamecontext=ctx,
            game_context_str=ctx_md,
            user_input=player_input,
            template_tags=tags,
        )

    def get_response_schema(self) -> Optional[dict]:
        """Extrae el JSON schema del modelo de respuesta esperado."""
        if self.response_model and hasattr(self.response_model, "model_json_schema"):
            return self.response_model.model_json_schema()
        return None

    def validate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: Optional[R] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Valida condiciones previas o la respuesta producida por el LLM."""
        return True, None, None

    def mutate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: R,
        is_valid: bool,
        metadata: Optional[dict],
    ) -> None:
        """Aplica mutaciones de estado tras la validación."""
        pass

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: R,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict],
    ) -> ResultType:
        """Construye el objeto ResultType con el resultado final del turno."""
        msg = getattr(llm_response, "msg", "") or reason or ""
        return ResultType(
            success=is_valid,
            message=msg,
            data=metadata,
        )

    def execute(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: R,
    ) -> ResultType:
        """Template method que ejecuta la secuencia validate -> mutate -> build_result."""
        is_valid, reason, metadata = self.validate(game_state_controller, player_input, llm_response)
        self.mutate(game_state_controller, player_input, llm_response, is_valid, metadata)
        return self.build_result(game_state_controller, player_input, llm_response, is_valid, reason, metadata)
