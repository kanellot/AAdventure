"""Aplicador atómico de efectos argumentales (LoreEffects)."""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from engines.game.state_controller import GameStateController


class LoreEffectApplier:
    """Aplica de forma atómica y pura las mutaciones declaradas en los efectos de un LoreBlock."""

    @classmethod
    def apply_effects(
        cls,
        effects: List[Dict[str, Any]],
        ctrl: GameStateController,
        autonomous_push: List[Tuple[str, str]],
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
                except Exception:
                    pass

            # 6. Acciones Autónomas 'push'
            if eff.get("action") == "push" and eff.get("target"):
                tgt = eff.get("target")
                push_act = "TALK" if tgt in ctrl.npcs_by_id else "MOVE"
                autonomous_push.append((push_act, tgt))
