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
        self._triggered_intermediate_place = None
        self._is_blocked = False
        self._blocked_intermediate_place = None
        self._blocked_connection = None
        self._actual_destination_place = None

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
        self._is_blocked = False
        self._blocked_intermediate_place = None
        self._blocked_connection = None
        self._actual_destination_place = destination_place

        if origin_place and destination_place:
            nav_status, nav_conns, nav_places, stopping_place, blocked_conn = (
                PathCalculator.calculate_navigation_route(
                    game_state_controller.world_state.places_by_name,
                    origin_place.name,
                    destination_place.name,
                )
            )

            if nav_status == "blocked" and stopping_place:
                self._is_blocked = True
                self._blocked_intermediate_place = stopping_place
                self._blocked_connection = blocked_conn
                self._actual_destination_place = stopping_place
                destination_place = stopping_place
                path_taken = nav_places[1:-1] if len(nav_places) > 2 else []
            elif nav_places:
                path_taken = nav_places[1:-1] if len(nav_places) > 2 else []

            travel_time = TimeCalculator.calculate_travel_time_between_places(
                game_state_controller.world_state.places_by_name,
                origin_place.name,
                destination_place.name,
                travel_speed=game_state_controller.data.state.travel_speed,
            )

        self._triggered_lore = None
        self._triggered_intermediate_place = None
        directive = None

        if destination_place:
            router = LoreRouter.get_instance()
            clean_input = (player_input or "").strip()

            if self._is_blocked:
                # Recopilar todos los identificadores del destino bloqueado (nombre, id)
                blocked_target_ids = set()
                if self.target:
                    blocked_target_ids.add(str(self.target).strip().lower())
                if self._blocked_connection and getattr(self._blocked_connection, "target", None):
                    blocked_target_ids.add(str(self._blocked_connection.target).strip().lower())

                orig_target_place = None
                if hasattr(game_state_controller, "world_state") and game_state_controller.world_state:
                    p_by_name = getattr(game_state_controller.world_state, "places_by_name", {})
                    p_by_id = getattr(game_state_controller.world_state, "places_by_id", {})
                    for tid in list(blocked_target_ids):
                        orig_target_place = p_by_name.get(tid) or p_by_id.get(tid)
                        if orig_target_place:
                            blocked_target_ids.add(str(orig_target_place.id).strip().lower())
                            blocked_target_ids.add(str(orig_target_place.name).strip().lower())
                            break

                candidate_blocks = [
                    b for b in router.get_blocks_for_entity(destination_place, game_state_controller)
                    if router.is_block_accessible(b, game_state_controller) and b.state != "done"
                ]

                # Si no encontramos en destination_place, buscar entre todos los bloques accesibles
                # que contengan block_connections apuntando a la conexión bloqueada
                if not candidate_blocks:
                    all_blocks = router._get_all_blocks(game_state_controller)
                    for b in all_blocks:
                        if not router.is_block_accessible(b, game_state_controller) or b.state == "done":
                            continue
                        for eff in getattr(b, "effects", []):
                            for bc in getattr(eff, "block_connections", []):
                                if str(bc).strip().lower() in blocked_target_ids:
                                    candidate_blocks.append(b)
                                    break

                blocking_block = None
                blocking_effect = None
                for b in candidate_blocks:
                    # Comprobar effects lista
                    for eff in getattr(b, "effects", []):
                        for bc in getattr(eff, "block_connections", []):
                            if str(bc).strip().lower() in blocked_target_ids:
                                blocking_block = b
                                blocking_effect = eff
                                break
                        if blocking_block:
                            break
                    # Fallback retrocompatible a on_active
                    if not blocking_block and getattr(b, "on_active", None):
                        for bc in getattr(b.on_active, "block_connections", []):
                            if str(bc).strip().lower() in blocked_target_ids:
                                blocking_block = b
                                blocking_effect = b.on_active
                                break
                    if blocking_block:
                        break

                if not blocking_block and candidate_blocks:
                    blocking_block = candidate_blocks[0]
                    blocking_effect = getattr(blocking_block, "on_active", None)

                if blocking_block:
                    self._triggered_lore = blocking_block
                    # Obtener directiva específica de la entidad que bloquea o general del bloque
                    block_dir = ""
                    eff_target = getattr(blocking_effect, "target", None) if blocking_effect else None
                    if eff_target and hasattr(blocking_block, "get_directive_for_entity"):
                        block_dir = blocking_block.get_directive_for_entity(eff_target) or ""
                    if not block_dir:
                        block_dir = blocking_block.directive or ""

                    target_name = (orig_target_place.name if orig_target_place else self.target) or "su destino"
                    if block_dir:
                        directive = (
                            f"{block_dir}. El avance hacia '{target_name}' está bloqueado y "
                            f"el viaje se detiene aquí en {destination_place.name} (el jugador no puede continuar hacia '{target_name}')."
                        )
                    else:
                        directive = (
                            f"El camino hacia '{target_name}' se encuentra bloqueado y "
                            f"el viaje se detiene en {destination_place.name} (el jugador no puede continuar hacia '{target_name}')."
                        )
                    self._triggered_intermediate_place = None

            else:
                matched_res = router.route_move_lore(
                    destination_place=destination_place,
                    game_state=game_state_controller,
                    player_input=clean_input,
                    path_taken=path_taken,
                )
                if matched_res:
                    matched_lore, triggered_place = matched_res
                    self._triggered_lore = matched_lore
                    directive = matched_lore.directive
                    if triggered_place.id != destination_place.id:
                        self._triggered_intermediate_place = triggered_place
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
                        if router.last_evaluation and router.last_evaluation.injected_directive:
                            directive = router.last_evaluation.injected_directive
                        else:
                            p_id = getattr(destination_place, "id", None) or getattr(destination_place, "name", None)
                            directive = self._triggered_lore.get_directive_for_entity(p_id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive
                    else:
                        proactive_block = router.find_proactive_lore(destination_place, game_state_controller)
                        matched_entity = destination_place
                        if not proactive_block and destination_place:
                            for entity_id in getattr(destination_place, "visible_entities", []):
                                npc_obj = (
                                    game_state_controller.world_state.npcs.get(entity_id)
                                    or getattr(game_state_controller.world_state, "npcs_by_name", {}).get(entity_id)
                                )
                                if npc_obj:
                                    proactive_block = router.find_proactive_lore(npc_obj, game_state_controller, npc=npc_obj)
                                    if proactive_block:
                                        matched_entity = npc_obj
                                        break
                        if proactive_block:
                            self._triggered_lore = proactive_block
                            p_id = getattr(matched_entity, "id", None) or getattr(matched_entity, "name", None)
                            directive = self._triggered_lore.get_directive_for_entity(p_id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive

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
        if is_valid:
            target_loc = None
            if self._actual_destination_place:
                target_loc = self._actual_destination_place.name
            elif self.target:
                target_loc = self.target

            if target_loc:
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
