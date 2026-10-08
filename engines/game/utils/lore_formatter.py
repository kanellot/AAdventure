"""Utilidades de formateo y construcción de proyecciones para LoreBlocks."""

from typing import Any


class LoreGraphFormatter:
    """Formatea condiciones, efectos y proyecciones del grafo de LoreBlocks para depuración."""

    @classmethod
    def format_condition_display(cls, cond: Any, is_met: bool, game_state_controller: Any) -> str:
        """Formatea una condición en texto descriptivo para el depurador."""
        etype = getattr(cond, "entity_type", "")
        eid = getattr(cond, "entity_id", "")
        sub = getattr(cond, "sub_condition", "")
        val = getattr(cond, "value", None)
        neg = getattr(cond, "is_negated", False)

        neg_prefix = "NO " if neg else ""
        gs = getattr(game_state_controller, "game_state", None)
        curr_loc = gs.current_location if gs else getattr(game_state_controller, "current_location", "")
        places_by_id = getattr(game_state_controller, "places_by_id", {})
        npcs_by_id = getattr(game_state_controller, "npcs_by_id", {})
        items_by_id = getattr(game_state_controller, "items_by_id", {})

        if etype == "place":
            p = places_by_id.get(eid)
            name_info = f"'{p.name}'" if p else eid
            if sub == "current_location":
                if is_met:
                    return f"{neg_prefix}Llegar a {name_info} (Actual: {curr_loc})"
                return f"{neg_prefix}Estar en {name_info} (Actual: {curr_loc or 'desconocido'})"
            elif sub == "visited":
                return f"{neg_prefix}Haber visitado el lugar {name_info}"
            elif sub in ("unlocked", "known"):
                return f"{neg_prefix}Lugar {name_info} descubierto"
            elif sub == "visible":
                return f"{neg_prefix}Lugar {name_info} visible en niebla de guerra"

        elif etype == "npc":
            npc = npcs_by_id.get(eid)
            npc_name = npc.name if npc else (eid or "NPC")
            if sub == "talk":
                curr_state = gs.player_state if gs else getattr(game_state_controller, "player_state", "EXPLORE")
                curr_tgt = gs.player_target if gs else getattr(game_state_controller, "player_target", "")
                if is_met:
                    return f"{neg_prefix}Hablar con {npc_name} (En diálogo actualmente)"
                return f"{neg_prefix}Iniciar diálogo con {npc_name} (Actual: {curr_state} -> '{curr_tgt}')"
            elif sub == "affinity":
                aff_val = float(val or 0.5)
                curr_aff = game_state_controller.get_npc_affinity(eid) if hasattr(game_state_controller,
                                                                                  "get_npc_affinity") else (
                    npc.affinity if npc else 0.5)
                return f"{neg_prefix}Afinidad con {npc_name} >= {aff_val:.2f} (Actual: {curr_aff:.2f})"
            elif sub == "affinity_range":
                curr_aff = game_state_controller.get_npc_affinity(eid) if hasattr(game_state_controller,
                                                                                  "get_npc_affinity") else (
                    npc.affinity if npc else 0.5)
                return f"{neg_prefix}Afinidad con {npc_name} en rango {val} (Actual: {curr_aff:.2f})"
            elif sub == "known":
                return f"{neg_prefix}Conocer a {npc_name}"
            elif sub == "visible":
                return f"{neg_prefix}NPC {npc_name} visible en niebla de guerra"

        elif etype == "item":
            it = items_by_id.get(eid)
            item_name = it.name if it else eid
            if sub in ("have", "inventory"):
                curr_inv = gs.inventory.items if gs else []
                has_item = eid in curr_inv
                return f"{neg_prefix}Tener en inventario '{item_name}' (Posee: {'Sí' if has_item else 'No'})"
            elif sub == "visible":
                return f"{neg_prefix}Objeto '{item_name}' visible"

        elif etype == "loreblock":
            if sub in ("child_done", "any_child_done"):
                return f"{neg_prefix}Algún sub-bloque hijo completado (done)"
            elif sub == "all_children_done":
                return f"{neg_prefix}Todos los sub-bloques hijos completados (done)"
            elif sub == "active":
                return f"{neg_prefix}LoreBlock '{eid}' en estado ACTIVE"
            elif sub == "done":
                return f"{neg_prefix}LoreBlock '{eid}' completado (DONE)"

        elif etype == "gold":
            req_gold = int(val or 0)
            curr_gold = gs.gold if gs else getattr(game_state_controller, "gold", 0)
            return f"{neg_prefix}Oro >= {req_gold} (Actual: {curr_gold})"

        elif etype == "time" or sub == "time_range":
            curr_t = gs.current_time if gs else "Día 1, 08:00"
            return f"{neg_prefix}Franja de tiempo en rango {val} (Tiempo actual: {curr_t})"

        return f"{neg_prefix}{etype}:{eid} ({sub}={val})"

    @classmethod
    def format_single_effect_summary(cls, effects: Any) -> str:
        """Resume un único efecto de LoreEffects en una cadena limpia."""
        if not effects:
            return "(Sin efectos)"
        parts = []
        gold = getattr(effects, "gold_delta", 0) or (effects.get("gold_delta", 0) if isinstance(effects, dict) else 0)
        if gold != 0:
            parts.append(f"{gold:+d} oro")

        aff = getattr(effects, "affinity_delta", 0.0) or (
            effects.get("affinity_delta", 0.0) if isinstance(effects, dict) else 0.0)
        if aff != 0.0:
            parts.append(f"Afinidad {aff:+.2f}")

        give_items = getattr(effects, "give_items", []) or (
            effects.get("give_items", []) if isinstance(effects, dict) else [])
        for it in give_items:
            parts.append(f"+Ítem: {it}")

        take_items = getattr(effects, "take_items", []) or (
            effects.get("take_items", []) if isinstance(effects, dict) else [])
        for it in take_items:
            parts.append(f"-Ítem: {it}")

        unlock_places = getattr(effects, "unlock_places", []) or (
            effects.get("unlock_places", []) if isinstance(effects, dict) else [])
        for p in unlock_places:
            parts.append(f"Lugar: {p}")

        block_places = getattr(effects, "block_places", []) or (
            effects.get("block_places", []) if isinstance(effects, dict) else [])
        for p in block_places:
            parts.append(f"🚫 Bloquear: {p}")

        unblock_places = getattr(effects, "unblock_places", []) or (
            effects.get("unblock_places", []) if isinstance(effects, dict) else [])
        for p in unblock_places:
            parts.append(f"🟢 Desbloquear: {p}")

        action = getattr(effects, "action", "") or (effects.get("action", "") if isinstance(effects, dict) else "")
        target = getattr(effects, "target", "") or (effects.get("target", "") if isinstance(effects, dict) else "")
        if action == "push" and target:
            parts.append(f"⚡ Push autónomo -> {target}")

        return ", ".join(parts) if parts else "(Sin mutaciones de estado)"

    @classmethod
    def format_effects_summary(cls, effects: Any) -> str:
        """Resume una lista o instancia de LoreEffects en una cadena."""
        if not effects:
            return "(Sin efectos)"
        if isinstance(effects, list):
            items_str = []
            for eff in effects:
                s = cls.format_single_effect_summary(eff)
                target = getattr(eff, "target", None) or (eff.get("target") if isinstance(eff, dict) else None)
                directive = getattr(eff, "directive", "") or (eff.get("directive", "") if isinstance(eff, dict) else "")
                tgt_prefix = f"[{target}]: " if target else ""
                if s and s != "(Sin mutaciones de estado)":
                    items_str.append(f"{tgt_prefix}{s}")
                elif directive:
                    dir_snip = directive[:25] + "..." if len(directive) > 25 else directive
                    items_str.append(f"{tgt_prefix}\"{dir_snip}\"")
            return " | ".join(items_str) if items_str else "(Sin efectos)"
        return cls.format_single_effect_summary(effects)
