"""Aplicador atómico de efectos argumentales (LoreEffects)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, NamedTuple, Tuple

logger = logging.getLogger(__name__)

from engines.game.state_controller import GameStateController


class AutonomousPushAction(NamedTuple):
    """Acción autónoma proactiva ('push') generada por un efecto de Lore."""

    action: str
    target: str
    directive: str = ""
    bypass_llm: bool = False


class LoreEffectApplier:
    """Aplica de forma atómica y pura las mutaciones declaradas en los efectos de un LoreBlock."""

    @classmethod
    def apply_block_effects(
            cls,
            blocks: List[Dict[str, Any]],
            phase: str,  # "active" | "done"
            ctrl: GameStateController,
            autonomous_push: Optional[List[AutonomousPushAction]] = None,
    ) -> List[AutonomousPushAction]:
        """Aplica de forma parametrizada los efectos correspondientes a la fase ('active' o 'done').

        Retorna la lista acumulada de acciones push autónomas generadas.
        """
        push_actions = autonomous_push if autonomous_push is not None else []
        for blk in blocks:
            if phase == "active":
                effects = blk.get("active_effects", []) or blk.get("effects", [])
            else:
                effects = blk.get("done_effects", [])

            if effects:
                cls.apply_effects(effects, ctrl, push_actions)


        return push_actions

    @classmethod
    def apply_effects(
            cls,
            effects: List[Dict[str, Any]],
            ctrl: GameStateController,
            autonomous_push: List[AutonomousPushAction],
    ) -> None:
        """Ejecuta la lista de efectos sobre el estado canónico y detecta acciones autónomas 'push'."""
        for eff in effects:
            if not isinstance(eff, dict):
                continue

            # 1. Revelación en Niebla de Guerra
            for pid in eff.get("unlock_places", []):
                for loc in ctrl.game_state.entity_map:
                    for p in loc.places:
                        if p.id == pid and p.status == "hidden":
                            p.status = "visible"

            for nid in eff.get("unlock_npcs", []):
                for loc in ctrl.game_state.entity_map:
                    for p in loc.places:
                        for npc in p.npcs:
                            if npc.id == nid:
                                npc.status = "visible"

            for iid in eff.get("unlock_items", []):
                for loc in ctrl.game_state.entity_map:
                    for p in loc.places:
                        for it in p.items:
                            if it.id == iid:
                                it.visible = True

            # 2. Bloqueo y Desbloqueo Espacial
            for pid in eff.get("block_places", []):
                ctrl.block_place(pid)

            for pid in eff.get("unblock_places", []):
                ctrl.unblock_place(pid)

            # 3. Inventario y Oro
            for iid in eff.get("give_items", []):
                ctrl.add_to_inventory(iid)

            for iid in eff.get("take_items", []):
                if iid in ctrl.game_state.inventory.items:
                    ctrl.remove_from_inventory(iid)

            if eff.get("gold_delta"):
                ctrl.game_state.gold += int(eff.get("gold_delta", 0))

            # 4. Afinidad
            if eff.get("affinity_delta") and eff.get("target"):
                tgt_npc = eff.get("target")
                curr_aff = ctrl.get_npc_affinity(tgt_npc) or 0.5
                ctrl.update_npc_affinity(tgt_npc, curr_aff + float(eff.get("affinity_delta", 0.0)))

            # 5. Avance de Tiempo
            if eff.get("elapsed_time"):
                t_str = str(eff.get("elapsed_time", "00:00"))
                try:
                    parts = t_str.split(":")
                    mins = int(parts[0]) * 60 + int(parts[1])
                    if mins > 0:
                        ctrl.add_elapsed_minutes(mins)
                except (ValueError, IndexError) as e:
                    logger.debug("Error al parsear elapsed_time '%s': %s", t_str, e)

            # 6. Acciones Autónomas 'push'
            if eff.get("action") == "push":
                tgt = eff.get("target")
                directive = str(eff.get("directive") or "")
                bypass_llm = bool(eff.get("bypass_llm", False))

                if not tgt:
                    act = "LOOK"
                    resolved_tgt = ctrl.game_state.current_location
                elif tgt in ctrl.npcs_by_id:
                    act = "TALK"
                    resolved_tgt = tgt
                elif hasattr(ctrl, "npcs_by_name") and tgt in ctrl.npcs_by_name:
                    act = "TALK"
                    resolved_tgt = ctrl.npcs_by_name[tgt].id
                elif tgt in ctrl.items_by_id:
                    act = "LOOK"
                    resolved_tgt = tgt
                elif hasattr(ctrl, "items_by_name") and tgt in ctrl.items_by_name:
                    act = "LOOK"
                    resolved_tgt = ctrl.items_by_name[tgt].id
                elif tgt in ctrl.places_by_id:
                    act = "LOOK"
                    resolved_tgt = tgt
                elif hasattr(ctrl, "places_by_name") and tgt in ctrl.places_by_name:
                    act = "LOOK"
                    resolved_tgt = ctrl.places_by_name[tgt].id
                else:
                    act = "LOOK"
                    resolved_tgt = ctrl.game_state.current_location

                autonomous_push.append(
                    AutonomousPushAction(
                        action=act,
                        target=resolved_tgt,
                        directive=directive,
                        bypass_llm=bypass_llm,
                    )
                )
