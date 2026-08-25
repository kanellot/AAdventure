from typing import Type, Optional, Tuple
from domains import Place, MoveNarratorCtx, MoveNarratorResponse, MoveNarratorResult
from game_engine.actions.behaviour import Behaviour
from game_engine.state import GameStateController

class MoveNarratorAction(Behaviour[MoveNarratorCtx, MoveNarratorResponse]):
    """Acción de narración de movimiento y actualización de localización."""

    def __init__(self, target: Optional[str]):
        self.target = target

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/exploration_move.md"

    @property
    def response_model(self) -> Type[MoveNarratorResponse]:
        return MoveNarratorResponse

    @property
    def profile_name(self) -> str:
        return "move_narrator"

    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> MoveNarratorCtx:
        origin_place = game_state_controller.data.place
        
        destination_place = None
        if self.target:
            if self.target in game_state_controller.world_state.places_by_id:
                destination_place = game_state_controller.world_state.places_by_id[self.target]
            elif self.target in game_state_controller.world_state.places_by_name:
                destination_place = game_state_controller.world_state.places_by_name[self.target]

        return MoveNarratorCtx(
            origin_place=origin_place,
            destination_place=destination_place,
            player_input=player_input
        )

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[MoveNarratorResponse] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        # En esta acción no es necesario validar nada
        return True, None, None

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: MoveNarratorResponse, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        if is_valid and self.target:
            game_state_controller.update_location(self.target)

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: MoveNarratorResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> MoveNarratorResult:
        return MoveNarratorResult(
            success=is_valid,
            message=llm_response.msg,
            data=metadata
        )
