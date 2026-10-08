"""Validador de reglas físicas, desenganche universal y alcance espacial."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from domains.projections import TurnOutput
from engines.game.state_controller import GameStateController
from engines.game.utils.path_calculator import PathCalculator


@dataclass
class ActionValidationResult:
    """Resultado de la verificación física y semántica de una acción."""

    is_valid: bool
    action_name: str
    resolved_target: str
    error_output: Optional[TurnOutput] = None
    traversed_places: List[Any] = field(default_factory=list)
    traversed_conns: List[Any] = field(default_factory=list)
    blocked_place_obstacle: Optional[Any] = None


class RulesValidator:
    """Valida entradas de usuario, colisiones, alcance visual y desenganche universal."""

    @classmethod
    def validate(
            cls,
            action: str,
            target: Optional[str],
            player_input: str,
            ctrl: GameStateController,
    ) -> ActionValidationResult:
        """Verifica la acción solicitada según el estado del jugador y la física del mundo."""
        curr_state = ctrl.game_state.player_state
        action_name = action.strip().upper() if action else ""
        raw_target = target.strip() if target else ""

        # 1. Regla de Texto Libre según player_state
        if not action_name and player_input:
            if curr_state == "EXPLORE":
                return ActionValidationResult(
                    is_valid=False,
                    action_name="",
                    resolved_target="",
                    error_output=TurnOutput(
                        author="SYSTEM",
                        type="msg",
                        msg="Debes seleccionar una acción (desplazarte, hablar u observar) para interactuar.",
                        player_state="EXPLORE",
                    ),
                )
            elif curr_state == "TALK":
                action_name = "TALK"
                raw_target = ctrl.game_state.player_target or ""
            elif curr_state == "LOOK":
                action_name = "LOOK"
                raw_target = ctrl.game_state.player_target or ctrl.game_state.current_location

        # 2. Validación por Tipo de Acción
        if action_name == "MOVE":
            return cls._validate_move(raw_target, curr_state, ctrl)
        elif action_name == "TALK":
            return cls._validate_talk(raw_target, curr_state, ctrl)
        elif action_name == "LOOK":
            return cls._validate_look(raw_target, curr_state, ctrl)
        else:
            return ActionValidationResult(
                is_valid=False,
                action_name=action_name,
                resolved_target=raw_target,
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg=f"Acción '{action_name}' no reconocida.",
                    player_state=curr_state,
                ),
            )

    @classmethod
    def _validate_move(cls, raw_target: str, curr_state: str, ctrl: GameStateController) -> ActionValidationResult:
        if not raw_target:
            return ActionValidationResult(
                is_valid=False,
                action_name="MOVE",
                resolved_target="",
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg="Debes indicar un destino para desplazarte.",
                    player_state=curr_state,
                ),
            )

        resolved_target = raw_target
        if raw_target not in ctrl.places_by_id:
            for p in ctrl.places_by_id.values():
                if p.name.lower() == raw_target.lower():
                    resolved_target = p.id
                    break

        status, conns, places_path, blocked_place = PathCalculator.calculate_navigation_route(
            ctrl.places_by_id,
            ctrl.game_state.current_location,
            resolved_target,
        )

        if status == "unreachable" or not places_path:
            return ActionValidationResult(
                is_valid=False,
                action_name="MOVE",
                resolved_target=resolved_target,
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg=f"No hay camino conocido hacia '{raw_target}'.",
                    player_state=curr_state,
                ),
            )

        if status == "blocked" and len(places_path) <= 1:
            obs_name = blocked_place.name if blocked_place else raw_target
            return ActionValidationResult(
                is_valid=False,
                action_name="MOVE",
                resolved_target=resolved_target,
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg=f"El camino hacia '{raw_target}' está bloqueado en '{obs_name}'.",
                    player_state=curr_state,
                ),
            )

        return ActionValidationResult(
            is_valid=True,
            action_name="MOVE",
            resolved_target=resolved_target,
            traversed_places=places_path,
            traversed_conns=conns,
            blocked_place_obstacle=blocked_place,
        )

    @classmethod
    def _validate_talk(cls, raw_target: str, curr_state: str, ctrl: GameStateController) -> ActionValidationResult:
        if not raw_target:
            return ActionValidationResult(
                is_valid=False,
                action_name="TALK",
                resolved_target="",
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg="Debes indicar con quién deseas hablar.",
                    player_state=curr_state,
                ),
            )

        resolved_target = raw_target
        if raw_target not in ctrl.npcs_by_id:
            for n in ctrl.npcs_by_id.values():
                if n.name.lower() == raw_target.lower():
                    resolved_target = n.id
                    break

        if not cls.is_npc_at_location(resolved_target, ctrl.game_state.current_location, ctrl):
            npc_obj = ctrl.npcs_by_id.get(resolved_target)
            name = npc_obj.name if npc_obj else raw_target
            return ActionValidationResult(
                is_valid=False,
                action_name="TALK",
                resolved_target=resolved_target,
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg=f"El personaje '{name}' no se encuentra aquí.",
                    player_state=curr_state,
                ),
            )

        return ActionValidationResult(
            is_valid=True,
            action_name="TALK",
            resolved_target=resolved_target,
        )

    @classmethod
    def _validate_look(cls, raw_target: str, curr_state: str, ctrl: GameStateController) -> ActionValidationResult:
        if not raw_target:
            raw_target = ctrl.game_state.current_location

        resolved_target = raw_target
        found = False
        for p in ctrl.places_by_id.values():
            if p.name.lower() == raw_target.lower():
                resolved_target = p.id
                found = True
                break
        if not found:
            for n in ctrl.npcs_by_id.values():
                if n.name.lower() == raw_target.lower():
                    resolved_target = n.id
                    found = True
                    break
        if not found:
            for it in ctrl.items_by_id.values():
                if it.name.lower() == raw_target.lower():
                    resolved_target = it.id
                    break

        if not cls.is_entity_reachable_to_look(resolved_target, ctrl.game_state.current_location, ctrl):
            return ActionValidationResult(
                is_valid=False,
                action_name="LOOK",
                resolved_target=resolved_target,
                error_output=TurnOutput(
                    author="SYSTEM",
                    type="msg",
                    msg=f"'{raw_target}' no está a tu alcance para ser observado.",
                    player_state=curr_state,
                ),
            )

        return ActionValidationResult(
            is_valid=True,
            action_name="LOOK",
            resolved_target=resolved_target,
        )

    @staticmethod
    def is_npc_at_location(npc_id: str, place_id: str, ctrl: GameStateController) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == place_id:
                    return any(npc.id == npc_id for npc in p.npcs)
        return False

    @staticmethod
    def is_entity_reachable_to_look(entity_id: str, current_place_id: str, ctrl: GameStateController) -> bool:
        if entity_id == current_place_id:
            return True

        curr_p = ctrl.places_by_id.get(current_place_id)
        if curr_p and entity_id in curr_p.connections:
            return True

        if entity_id in ctrl.game_state.inventory:
            return True

        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == current_place_id:
                    if any(it.id == entity_id for it in p.items):
                        return True
                    if any(npc.id == entity_id for npc in p.npcs):
                        return True
        return False
