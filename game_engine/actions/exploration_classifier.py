from typing import Type, List, Optional

from domains import (
    ResultType,
    ContextType,
    ResponseType,
    LocationInfo,
    PlaceInfo,
    NPCInfo,
)
from game_engine.actions.behaviour import Behaviour
from game_engine.state import GameStateController

### DATA CLASSES ###
# Context
class ExplorationClassifierCtx(ContextType):
    location: LocationInfo
    places: List[PlaceInfo]
    npcs: List[NPCInfo]
    player_input: Optional[str] = None

    def to_markdown(self) -> str:
        md = f"## LOCALIZACIÓN\n- `{self.location.id}`: {self.location.nombre}\n\n"
        
        md += "## LUGARES EN LA LOCALIZACIÓN\n"
        if self.places:
            for p in self.places:
                md += f"- `{p.id}`: {p.nombre}\n"
        else:
            md += "- (Ninguno)\n"
            
        md += "\n## NPCS EN LA LOCALIZACIÓN\n"
        if self.npcs:
            for n in self.npcs:
                md += f"- `{n.id}`: {n.nombre}\n"
        else:
            md += "- (Ninguno)\n"
        return md

# LLM response
class ExplorationClassifierResponse(ResponseType):
    action: Optional[str] = None
    target: Optional[str] = None
# Game engine response
class ExplorationResult(ResultType):
    result: str
    action: Optional[str] = None
    target: Optional[str] = None

### ACTION CLASS ###
class ExplorationClassifierAction(Behaviour[ExplorationClassifierCtx, ExplorationClassifierResponse]):
    """Paso 1 del turno: Clasifica el input del jugador para determinar la acción de exploración deseada."""

    ACTIONS = ["MOVE", "LOOK", "TALK"]

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/classifier.md"

    @property
    def response_model(self) -> Type[ExplorationClassifierResponse]:
        return ExplorationClassifierResponse

    @property
    def profile_name(self) -> str:
        return "exploration_classifier"

    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> ExplorationClassifierCtx:
        places_in_current_location = []
        location_info = LocationInfo(id="unknown", nombre="Desconocido")
        npcs_in_current_location = []
        
        loc_dict = game_state_controller.get_current_location()
        if loc_dict:
            location_info = LocationInfo(id=loc_dict["id"], nombre=loc_dict["name"])
            places_in_current_location = [
                PlaceInfo(id=p["id"], nombre=p["name"]) for p in game_state_controller.get_places_list()
            ]
            npcs_in_current_location = [
                NPCInfo(id=n["id"], nombre=n["name"]) for n in game_state_controller.get_npc_list()
            ]

        return ExplorationClassifierCtx(
            location=location_info,
            places=places_in_current_location,
            npcs=npcs_in_current_location,
            player_input=player_input
        )

    @staticmethod
    def _get_current_location_entities(
        game_state_controller: GameStateController
    ) -> tuple[set[str], set[str], set[str], set[str]]:
        place_ids = set()
        place_names = set()
        npc_ids = set()
        npc_names = set()
        
        for p in game_state_controller.get_places_list():
            place_ids.add(p["id"])
            place_names.add(p["name"])
            
        for n in game_state_controller.get_npc_list():
            npc_ids.add(n["id"])
            npc_names.add(n["name"])
            
        return place_ids, place_names, npc_ids, npc_names

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[ExplorationClassifierResponse] = None
    ) -> tuple[bool, Optional[str], Optional[dict]]:
        if llm_response is None:
            return True, None, None

        action: Optional[str] = llm_response.action.upper() if llm_response.action else None
        target: Optional[str] = llm_response.target if llm_response.target else None
        
        metadata = {
            "action": action,
            "target": target
        }

        if not action:
            return False, "No se especificó ninguna acción.", metadata
        if action not in self.ACTIONS:
            return False, f"Tipo de acción '{action}' desconocido.", metadata
            
        if not target:
            return False, "No se especificó ningún target.", metadata
            
        place_ids, place_names, npc_ids, npc_names = self._get_current_location_entities(game_state_controller)
        
        if (target not in place_ids and 
            target not in place_names and 
            target not in npc_ids and 
            target not in npc_names):
            return False, f"El target '{target}' no pertenece a la localización actual.", metadata
            
        return True, "Acción clasificada correctamente.", metadata

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: ExplorationClassifierResponse, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        if is_valid and metadata and metadata.get("action") == "TALK":
            target = metadata.get("target")
            npc = None
            for n in game_state_controller.data.npcs.values():
                if n.id == target or n.name == target:
                    npc = n
                    break
            if not npc:
                npc = game_state_controller.load_npc(target)

            if npc:
                game_state_controller.update_state("TALK")
                game_state_controller.data.state.player_target = npc.name
                
                # Move to the NPC's place if not already there
                npc_place = None
                world_state = game_state_controller.world_state
                for place in world_state.places_by_id.values():
                    if npc.id in place.visible_entities:
                        npc_place = place
                        break
                if npc_place:
                    game_state_controller.update_location(npc_place.name)

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: ExplorationClassifierResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> ExplorationResult:
        action = metadata.get("action") if metadata else None
        target = metadata.get("target") if metadata else None
        
        if is_valid:
            return ExplorationResult(
                success=True,
                message=reason or "Acción clasificada correctamente.",
                result="success",
                action=action,
                target=target,
                data=metadata
            )
        else:
            return ExplorationResult(
                success=False,
                message=f"Acción rechazada: {reason}",
                result="fail",
                action=action,
                target=target,
                data={
                    "reason": reason
                }
            )



