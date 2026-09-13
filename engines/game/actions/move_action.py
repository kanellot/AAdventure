"""Acción de narración de movimiento y actualización de localización."""

from typing import Dict, Optional, Tuple, Type
from domains import MoveNarratorCtx, MoveNarratorResponse, MoveNarratorResult, Place
from engines.game.actions.base_action import BaseAction
from engines.game.lore_router import LoreRouter
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter, PathCalculator, TimeCalculator


class MoveAction(BaseAction[MoveNarratorCtx, MoveNarratorResponse]):
    """Acción de desplazamiento: calcula ruta, tiempo, lore dinámico y traslada al jugador."""

    def __init__(self, target: Optional[str]):
        self.target = target
        self._triggered_lore = None

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/exploration_move.md"

    @property
    def response_model(self) -> Type[MoveNarratorResponse]:
        return MoveNarratorResponse

    @property
    def profile_name(self) -> str:
        return "move_narrator"

    def get_template_tags(self, ctx: MoveNarratorCtx) -> Dict[str, str]:
        """Genera los tags runtime formateados para la plantilla de movimiento."""
        return MarkdownFormatter.move_tags(ctx)

    def to_markdown(self, ctx: MoveNarratorCtx) -> str:
        """Genera la representación Markdown de respaldo del contexto."""
        return MarkdownFormatter.move_markdown(ctx)

    def build_context(
        self,
        game_state_controller: GameStateController,
        player_input: str,
    ) -> MoveNarratorCtx:
        """Construye el contexto de navegación entre lugares evaluando lore dinámico."""
        origin_place = game_state_controller.data.place
        destination_place = None

        if self.target:
            if self.target in game_state_controller.world_state.places_by_id:
                destination_place = game_state_controller.world_state.places_by_id[self.target]
            elif self.target in game_state_controller.world_state.places_by_name:
                destination_place = game_state_controller.world_state.places_by_name[self.target]
            else:
                for p in game_state_controller.world_state.places_by_id.values():
                    if self.target in p.visible_entities:
                        destination_place = p
                        break
                if not destination_place:
                    for npc in game_state_controller.world_state.npcs.values():
                        if npc.name == self.target or npc.id == self.target:
                            for p in game_state_controller.world_state.places_by_id.values():
                                if npc.id in p.visible_entities or npc.name in p.visible_entities:
                                    destination_place = p
                                    break
                            break

        path_taken = []
        travel_time = 0
        if origin_place and destination_place:
            path_taken = PathCalculator.find_intermediate_places(
                game_state_controller.world_state.places_by_name,
                origin_place.name,
                destination_place.name,
            )
            travel_time = TimeCalculator.calculate_travel_time_between_places(
                game_state_controller.world_state.places_by_name,
                origin_place.name,
                destination_place.name,
                travel_speed=game_state_controller.data.state.travel_speed,
            )

        self._triggered_lore = None
        directive = None

        if destination_place:
            router = LoreRouter.get_instance()
            clean_input = (player_input or "").strip()
            matched_lore = router.route_move_lore(
                destination_place=destination_place,
                game_state=game_state_controller,
                player_input=clean_input,
                path_taken=path_taken,
            )
            if matched_lore:
                self._triggered_lore = matched_lore
                directive = matched_lore.directive
            else:
                match = None
                if clean_input:
                    match = router.find_reactive_lore(clean_input, destination_place, game_state_controller)
                    if not match and path_taken:
                        for intermediate_place in path_taken:
                            match = router.find_reactive_lore(clean_input, intermediate_place, game_state_controller)
                            if match:
                                break
                if match:
                    self._triggered_lore, _ = match
                    directive = self._triggered_lore.directive
                else:
                    proactive_block = router.find_proactive_lore(destination_place, game_state_controller)
                    if proactive_block:
                        self._triggered_lore = proactive_block
                        directive = self._triggered_lore.directive

        return MoveNarratorCtx(
            origin_place=origin_place,
            destination_place=destination_place,
            player_input=player_input,
            path_taken=path_taken,
            estimated_travel_time=travel_time,
            directive=directive,
        )

    def validate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: Optional[MoveNarratorResponse] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        return True, None, None

    def mutate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: MoveNarratorResponse,
        is_valid: bool,
        metadata: Optional[dict],
    ) -> None:
        if is_valid and self.target:
            target_loc = self.target
            if (
                target_loc not in game_state_controller.world_state.places_by_name
                and target_loc not in game_state_controller.world_state.places_by_id
            ):
                for p in game_state_controller.world_state.places_by_id.values():
                    if target_loc in p.visible_entities:
                        target_loc = p.name
                        break
                else:
                    for npc in game_state_controller.world_state.npcs.values():
                        if npc.name == target_loc or npc.id == target_loc:
                            for p in game_state_controller.world_state.places_by_id.values():
                                if npc.id in p.visible_entities or npc.name in p.visible_entities:
                                    target_loc = p.name
                                    break
                            break
            game_state_controller.update_location(target_loc)

            if self._triggered_lore:
                router = LoreRouter.get_instance()
                router.apply_effects(self._triggered_lore, game_state_controller)

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: MoveNarratorResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict],
    ) -> MoveNarratorResult:
        return MoveNarratorResult(
            success=is_valid,
            message=llm_response.msg,
            data=metadata,
        )
