from typing import Type, Optional, Tuple, Union
from domains import Place, NPC, ExplainLookNarratorCtx, ExplainLookResponse, ExplainLookResult
from game_engine.actions.behaviour import Behaviour
from game_engine.state import GameStateController

class ExplainLookNarratorAction(Behaviour[ExplainLookNarratorCtx, ExplainLookResponse]):
    """Acción de explicación o inspección detallada de un lugar o NPC, que también maneja fallos."""

    def __init__(self, target: Optional[str] = None, failed_reason: Optional[str] = None):
        self.target = target
        self.failed_reason = failed_reason

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/explain_look.md"

    @property
    def response_model(self) -> Type[ExplainLookResponse]:
        return ExplainLookResponse

    @property
    def profile_name(self) -> str:
        return "explain_look_narrator"

    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> ExplainLookNarratorCtx:
        entity = None
        target = self.target

        if not target:
            entity = game_state_controller.data.place
        else:
            # 1. Buscar en NPCs visibles locales
            for n in game_state_controller.data.npcs.values():
                if n.id == target or n.name == target:
                    entity = n
                    break
            
            # 2. Buscar en Places
            if not entity:
                current_place = game_state_controller.data.place
                if current_place and (current_place.id == target or current_place.name == target):
                    entity = current_place
                else:
                    if target in game_state_controller.world_state.places_by_id:
                        entity = game_state_controller.world_state.places_by_id[target]
                    elif target in game_state_controller.world_state.places_by_name:
                        entity = game_state_controller.world_state.places_by_name[target]
            
            # Si no se encuentra, usar el lugar actual como respaldo
            if not entity:
                entity = game_state_controller.data.place

        return ExplainLookNarratorCtx(
            entity=entity,
            player_input=player_input,
            failed_reason=self.failed_reason
        )

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[ExplainLookResponse] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        # En esta acción no es necesario validar nada
        return True, None, None

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: ExplainLookResponse, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        if not is_valid or self.failed_reason or not self.target:
            return

        new_desc = llm_response.msg
        target = self.target

        # 1. Buscar si el target es un NPC
        npc = None
        for n in game_state_controller.data.npcs.values():
            if n.id == target or n.name == target:
                npc = n
                break
        
        if npc:
            # Añadir descripción en gamestate
            npc.description = f"{npc.description}\n{new_desc}"
            # Integrar en gameworld (world_state)
            if npc.id in game_state_controller.world_state.npcs:
                game_state_controller.world_state.npcs[npc.id].description = npc.description
            return

        # 2. Buscar si el target es un Place
        place = None
        current_place = game_state_controller.data.place
        if current_place and (current_place.id == target or current_place.name == target):
            place = current_place

        if not place:
            # Buscar en el world state
            if target in game_state_controller.world_state.places_by_id:
                place = game_state_controller.world_state.places_by_id[target]
            elif target in game_state_controller.world_state.places_by_name:
                place = game_state_controller.world_state.places_by_name[target]

        if place:
            # Añadir descripción en gamestate si coincide con el actual
            if current_place and place.id == current_place.id:
                current_place.description = f"{current_place.description}\n{new_desc}"
            # Integrar en gameworld (world_state)
            if place.id in game_state_controller.world_state.places_by_id:
                game_state_controller.world_state.places_by_id[place.id].description = f"{game_state_controller.world_state.places_by_id[place.id].description}\n{new_desc}"

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: ExplainLookResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> ExplainLookResult:
        return ExplainLookResult(
            success=is_valid and not self.failed_reason,
            message=llm_response.msg,
            data=metadata
        )
