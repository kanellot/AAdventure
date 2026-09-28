"""Evaluador de condiciones lógicas y semánticas de LoreBlocks."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from engines.embedding import EmbeddingEngine
from engines.game.state_controller import GameStateController


class LoreConditionEvaluator:
    """Evalúa predicados y grupos de condiciones sobre el estado del juego."""

    @classmethod
    def has_effective_active_conditions(cls, blk: Dict[str, Any]) -> bool:
        """Indica si el bloque contiene condiciones de activación reales o frases RAG."""
        for grp in blk.get("active_conditions", []) or []:
            grp_dict = grp if isinstance(grp, dict) else (grp.model_dump() if hasattr(grp, "model_dump") else {})
            if grp_dict.get("rag_enabled") and grp_dict.get("trigger_phrases"):
                return True
            if grp_dict.get("conditions"):
                return True
        return False

    @classmethod
    def has_effective_done_conditions(cls, blk: Dict[str, Any]) -> bool:
        """Indica si el bloque contiene condiciones de salida reales o frases RAG."""
        for grp in blk.get("done_conditions", []) or []:
            grp_dict = grp if isinstance(grp, dict) else (grp.model_dump() if hasattr(grp, "model_dump") else {})
            if grp_dict.get("rag_enabled") and grp_dict.get("trigger_phrases"):
                return True
            if grp_dict.get("conditions"):
                return True
        return False

    @classmethod
    def are_condition_groups_met(
        cls,
        groups: List[Any],
        ctrl: GameStateController,
        eval_query: str = "",
        precomputed_scores: Optional[Dict[str, float]] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
    ) -> bool:
        """Evalúa una lista de ConditionGroups con lógica OR entre grupos y AND interno."""
        if not groups:
            return False

        query_vec = None
        for grp in groups:
            grp_dict = grp if isinstance(grp, dict) else (grp.model_dump() if hasattr(grp, "model_dump") else {})
            rag_enabled = bool(grp_dict.get("rag_enabled"))
            trigger_phrases = grp_dict.get("trigger_phrases", [])

            # Evaluación RAG si el grupo lo requiere
            if rag_enabled and trigger_phrases:
                if not eval_query:
                    continue
                threshold = float(grp_dict.get("threshold") or 0.65)
                matched_rag = False
                for phrase in trigger_phrases:
                    if not phrase:
                        continue
                    if precomputed_scores and phrase in precomputed_scores:
                        score = precomputed_scores[phrase]
                    elif embedding_engine is not None:
                        if query_vec is None:
                            query_vec = embedding_engine.embed_text(eval_query)
                        p_vec = embedding_engine.embed_text(phrase)
                        score = float(embedding_engine.compute_similarity(query_vec, p_vec))
                    else:
                        score = 0.0

                    if score >= threshold:
                        matched_rag = True
                        break
                if not matched_rag:
                    continue

            conditions = grp_dict.get("conditions", [])
            if not conditions and not rag_enabled:
                continue

            all_met = True
            for c in conditions:
                c_dict = c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else {})
                met = cls.is_single_condition_met(c_dict, ctrl)
                if c_dict.get("is_negated"):
                    met = not met
                if not met:
                    all_met = False
                    break

            if all_met:
                return True

        return False

    @classmethod
    def is_single_condition_met(cls, c: Dict[str, Any], ctrl: GameStateController) -> bool:
        """Evalúa un predicado atómico frente al GameState canónico."""
        etype = c.get("entity_type", "").lower()
        eid = c.get("entity_id", "")
        sub = c.get("sub_condition", "").lower()
        val = c.get("value")

        # 1. Place
        if etype == "place":
            if sub == "current_location":
                return ctrl.game_state.current_location == (val or eid)
            elif sub == "visited":
                return cls._is_place_status(ctrl, eid, ("visited",))
            elif sub in ("visible", "known"):
                return cls._is_place_status(ctrl, eid, ("visited", "visible"))

        # 2. NPC
        elif etype == "npc":
            if sub == "talk":
                return ctrl.game_state.player_state == "TALK" and ctrl.game_state.player_target == eid
            elif sub == "affinity":
                aff = ctrl.get_npc_affinity(eid) or 0.5
                return aff >= float(val if val is not None else 0.5)
            elif sub == "affinity_range":
                aff = ctrl.get_npc_affinity(eid) or 0.5
                if isinstance(val, (list, tuple)) and len(val) == 2:
                    return float(val[0]) <= aff <= float(val[1])
                return aff >= float(val if val is not None else 0.5)
            elif sub == "visible":
                return cls._is_npc_at_location(ctrl, eid, ctrl.game_state.current_location)
            elif sub == "known":
                return cls._is_npc_known(ctrl, eid)
            elif sub == "current_location":
                target_loc = val or ctrl.game_state.current_location
                return cls._is_npc_at_location(ctrl, eid, target_loc)

        # 3. Item
        elif etype == "item":
            if sub in ("have", "inventory"):
                return eid in ctrl.game_state.inventory.items
            elif sub == "visible":
                return cls._is_item_visible_at_current(ctrl, eid)
            elif sub == "known":
                return (eid in ctrl.game_state.inventory.items) or cls._is_item_visible_anywhere(ctrl, eid)
            elif sub == "current_location":
                target_loc = val or ctrl.game_state.current_location
                return cls._is_item_at_location(ctrl, eid, target_loc)

        # 4. Gold
        elif etype == "gold":
            if sub in ("have", "amount"):
                return ctrl.game_state.gold >= int(val or 0)

        # 5. LoreBlock
        elif etype == "loreblock":
            if sub == "active":
                return any(b.get("id") == eid for b in ctrl.game_state.loreblocks.active)
            elif sub == "done":
                return any(b.get("id") == eid for b in ctrl.game_state.loreblocks.done)
            elif sub == "all_children_done":
                children = cls._get_block_children(ctrl, eid)
                return bool(children) and all(b.get("state") == "done" for b in children)
            elif sub == "any_child_done":
                children = cls._get_block_children(ctrl, eid)
                return any(b.get("state") == "done" for b in children)

        # 6. Time
        elif etype == "time":
            if sub == "time_range" and val:
                return cls._is_time_in_range(ctrl.game_state.current_time, str(val))

        # Simplificación de alias de Player: si entity_type es "player"
        elif etype == "player":
            if sub == "current_location":
                return ctrl.game_state.current_location == (val or eid)
            elif sub in ("gold", "have"):
                return ctrl.game_state.gold >= int(val or 0)
            elif sub in ("inventory", "have_item"):
                return (val or eid) in ctrl.game_state.inventory.items

        return False

    # -------------------------------------------------------------------------
    # Métodos Auxiliares Limpios de Consulta
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_place_status(ctrl: GameStateController, place_id: str, allowed_statuses: tuple) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == place_id:
                    return p.status in allowed_statuses
        return False

    @staticmethod
    def _is_npc_at_location(ctrl: GameStateController, npc_id: str, place_id: str) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == place_id:
                    return any(npc.id == npc_id for npc in p.npcs)
        return False

    @staticmethod
    def _is_npc_known(ctrl: GameStateController, npc_id: str) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                for npc in p.npcs:
                    if npc.id == npc_id:
                        return npc.status != "hidden"
        return False

    @staticmethod
    def _is_item_visible_at_current(ctrl: GameStateController, item_id: str) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == ctrl.game_state.current_location:
                    return any(it.id == item_id and it.visible for it in p.items)
        return False

    @staticmethod
    def _is_item_visible_anywhere(ctrl: GameStateController, item_id: str) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if any(it.id == item_id and it.visible for it in p.items):
                    return True
        return False

    @staticmethod
    def _is_item_at_location(ctrl: GameStateController, item_id: str, target_location: str) -> bool:
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == target_location:
                    return any(it.id == item_id for it in p.items)
        return False

    @staticmethod
    def _get_block_children(ctrl: GameStateController, parent_id: str) -> List[Dict[str, Any]]:
        all_blocks = (
            list(ctrl.game_state.loreblocks.active)
            + list(ctrl.game_state.loreblocks.unknown)
            + list(ctrl.game_state.loreblocks.done)
        )
        return [b for b in all_blocks if b.get("parent_id") == parent_id]

    @staticmethod
    def _is_time_in_range(current_time: Optional[str], val_range: str) -> bool:
        try:
            curr_time = current_time or "Día 1, 08:00"
            time_part = curr_time.split(", ")[-1] if ", " in curr_time else curr_time
            h_curr, m_curr = map(int, time_part.split(":"))
            curr_mins = h_curr * 60 + m_curr
            start_str, end_str = val_range.split("-")
            h_start, m_start = map(int, start_str.split(":"))
            h_end, m_end = map(int, end_str.split(":"))
            return (h_start * 60 + m_start) <= curr_mins <= (h_end * 60 + m_end)
        except Exception:
            return True
