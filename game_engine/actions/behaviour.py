from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, Tuple
from domains import ContextType, ResponseType, ResultType
from game_engine.state import GameStateController

C = TypeVar("C", bound=ContextType)
R = TypeVar("R", bound=ResponseType)

class Behaviour(ABC, Generic[C, R]):
    """Interfaz base (plantilla) para la definición de comportamientos (Steps) del juego."""

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
        """Nombre del perfil de inferencia (opcional, por defecto 'narrator')."""
        return "narrator"

    @abstractmethod
    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> C:
        """Construye y retorna el modelo de contexto para pasar al LLM."""
        pass

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[R] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Valida las condiciones previas (si llm_response es None) o la respuesta del LLM.
        Retorna (is_valid, reason, metadata). Por defecto es True sin error ni metadatos."""
        return True, None, None

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: R, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        """Aplica mutaciones al estado del juego basándose en el resultado de la validación."""
        pass

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: R,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> ResultType:
        """Construye el objeto de resultado ResultType de la ejecución del turno."""
        msg = getattr(llm_response, "msg", "") or reason or ""
        return ResultType(
            success=is_valid,
            message=msg,
            data=metadata
        )

    def execute(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: R
    ) -> ResultType:
        """Template Method que ejecuta el flujo estándar de un Step/Behaviour."""
        is_valid, reason, metadata = self.validate(game_state_controller, player_input, llm_response)
        self.mutate(game_state_controller, player_input, llm_response, is_valid, metadata)
        return self.build_result(game_state_controller, player_input, llm_response, is_valid, reason, metadata)


