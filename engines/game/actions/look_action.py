"""Acción de explicación o inspección detallada de un lugar, NPC u objeto."""

from typing import Dict, Optional, Tuple, Type
from domains import (
    Entity,
    ExplainLookNarratorCtx,
    ExplainLookResponse,
    ExplainLookResult,
    NPC,
    Place,
)
from engines.game.actions.base_action import BaseAction
from engines.game.lore_router import LoreRouter
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter


class LookAction(BaseAction[ExplainLookNarratorCtx, ExplainLookResponse]):
    """Acción de inspección: describe y explica entidades o lugares integrando lore."""

    def __init__(self, target: Optional[str] = None, failed_reason: Optional[str] = None):
        self.target = target
        self.failed_reason = failed_reason
        self._triggered_lore = None

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/explain_look.md"

    @property
    def response_model(self) -> Type[ExplainLookResponse]:
        return ExplainLookResponse

    @property
    def profile_name(self) -> str:
        return "explain_look_narrator"

    def get_template_tags(self, ctx: ExplainLookNarratorCtx) -> Dict[str, str]:
        """Genera los tags runtime formateados para la plantilla de inspección."""
        return MarkdownFormatter.explain_look_tags(ctx)

    def to_markdown(self, ctx: ExplainLookNarratorCtx) -> str:
        """Genera la representación Markdown de respaldo del contexto."""
        return MarkdownFormatter.explain_look_markdown(ctx)

    def build_context(
        self,
        game_state_controller: GameStateController,
        player_input: str,
    ) -> ExplainLookNarratorCtx:
        """Construye el contexto de inspección resolviendo la entidad consultada."""
        entity = None
        target = self.target

        if not target:
            entity = game_state_controller.data.place
        else:
            for n in game_state_controller.data.npcs.values():
                if n.id == target or n.name == target:
                    entity = n
                    break

            if not entity and hasattr(game_state_controller.world_state, "npcs"):
                for n in game_state_controller.world_state.npcs.values():
                    if n.id == target or n.name == target:
                        entity = n
                        break

            # Buscar en Objetos (Items)
            if not entity and hasattr(game_state_controller.world_state, "objects"):
                entity = (
                    game_state_controller.world_state.objects.get(target)
                    or game_state_controller.world_state.objects_by_name.get(target)
                )

            if not entity:
                current_place = game_state_controller.data.place
                if current_place and (current_place.id == target or current_place.name == target):
                    entity = current_place
                else:
                    if target in game_state_controller.world_state.places_by_id:
                        entity = game_state_controller.world_state.places_by_id[target]
                    elif target in game_state_controller.world_state.places_by_name:
                        entity = game_state_controller.world_state.places_by_name[target]

            if not entity and game_state_controller.data.place:
                for vent in game_state_controller.data.place.visible_entities:
                    if vent.lower() == target.lower() or vent.lower().endswith(target.lower()):
                        entity = Entity(
                            id=vent,
                            name=vent,
                            description=f"Elemento u objeto situado en {game_state_controller.data.place.name}.",
                        )
                        break

            if not entity:
                entity = game_state_controller.data.place

        router = LoreRouter.get_instance()
        self._triggered_lore = None
        directive = None

        has_dynamic_lore = (
            (entity and (getattr(entity, "dynamic_lore", None) or router.get_blocks_for_entity(entity, game_state_controller))) or
            (game_state_controller.data.place and (getattr(game_state_controller.data.place, "dynamic_lore", None) or router.get_blocks_for_entity(game_state_controller.data.place, game_state_controller)))
        )

        if has_dynamic_lore:
            clean_input = (player_input or "").strip()
            match = None
            if clean_input and entity:
                match = router.find_reactive_lore(clean_input, entity, game_state_controller)
                if not match and game_state_controller.data.place and game_state_controller.data.place != entity:
                    match = router.find_reactive_lore(clean_input, game_state_controller.data.place, game_state_controller)

            if match:
                self._triggered_lore, _ = match
                if router.last_evaluation and router.last_evaluation.injected_directive:
                    directive = router.last_evaluation.injected_directive
                else:
                    ent_id = getattr(entity, "id", None) or getattr(entity, "name", None)
                    directive = self._triggered_lore.get_directive_for_entity(ent_id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive
            else:
                proactive_block = None
                matched_entity = entity
                if entity:
                    proactive_block = router.find_proactive_lore(entity, game_state_controller)
                if not proactive_block and entity and hasattr(entity, "visible_entities"):
                    for e_id in getattr(entity, "visible_entities", []):
                        npc_obj = (
                            game_state_controller.world_state.npcs.get(e_id)
                            or getattr(game_state_controller.world_state, "npcs_by_name", {}).get(e_id)
                        )
                        if npc_obj:
                            proactive_block = router.find_proactive_lore(npc_obj, game_state_controller, npc=npc_obj)
                            if proactive_block:
                                matched_entity = npc_obj
                                break
                if not proactive_block and game_state_controller.data.place and game_state_controller.data.place != entity:
                    proactive_block = router.find_proactive_lore(game_state_controller.data.place, game_state_controller)
                    if proactive_block:
                        matched_entity = game_state_controller.data.place
                if proactive_block:
                    self._triggered_lore = proactive_block
                    ent_id = getattr(matched_entity, "id", None) or getattr(matched_entity, "name", None)
                    directive = self._triggered_lore.get_directive_for_entity(ent_id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive

        return ExplainLookNarratorCtx(
            entity=entity,
            inspection_history=[],
            player_input=player_input,
            directive=directive,
            failed_reason=self.failed_reason,
        )

    def validate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: Optional[ExplainLookResponse] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        return True, None, None

    def mutate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: ExplainLookResponse,
        is_valid: bool,
        metadata: Optional[dict],
    ) -> None:
        if not is_valid or self.failed_reason:
            return

        if self._triggered_lore:
            router = LoreRouter.get_instance()
            router.apply_effects(self._triggered_lore, game_state_controller)

        if not self.target:
            return

        new_desc = llm_response.msg
        target = self.target

        npc = None
        for n in game_state_controller.data.npcs.values():
            if n.id == target or n.name == target:
                npc = n
                break

        if npc:
            npc.description = f"{npc.description}\n{new_desc}"
            if npc.id in game_state_controller.world_state.npcs:
                game_state_controller.world_state.npcs[npc.id].description = npc.description
            return

        place = None
        current_place = game_state_controller.data.place
        if current_place and (current_place.id == target or current_place.name == target):
            place = current_place

        if not place:
            if target in game_state_controller.world_state.places_by_id:
                place = game_state_controller.world_state.places_by_id[target]
            elif target in game_state_controller.world_state.places_by_name:
                place = game_state_controller.world_state.places_by_name[target]

        if place:
            if current_place and place.id == current_place.id:
                current_place.description = f"{current_place.description}\n{new_desc}"
            if place.id in game_state_controller.world_state.places_by_id:
                game_state_controller.world_state.places_by_id[place.id].description = (
                    f"{game_state_controller.world_state.places_by_id[place.id].description}\n{new_desc}"
                )
            return

        # Objeto (Item)
        if hasattr(game_state_controller.world_state, "objects"):
            obj = (
                game_state_controller.world_state.objects.get(target)
                or game_state_controller.world_state.objects_by_name.get(target)
            )
            if obj:
                obj.description = f"{obj.description}\n{new_desc}"
                return

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: ExplainLookResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict],
    ) -> ExplainLookResult:
        return ExplainLookResult(
            success=is_valid and not self.failed_reason,
            message=llm_response.msg,
            data=metadata,
        )
