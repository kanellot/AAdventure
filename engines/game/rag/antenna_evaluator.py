"""Evaluador semántico de antenas RAG y selección de directivas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from domains.projections import RagAntennaScoreProjection, RagEvaluationProjection
from engines.embedding import EmbeddingEngine
from engines.game.lore.condition_evaluator import LoreConditionEvaluator
from engines.game.lore.state_machine import LoreStateMachine
from engines.game.state_controller import GameStateController


class RagAntennaEvaluator:
    """Evalúa la entrada del jugador contra las antenas de activación y salida RAG."""

    @classmethod
    def evaluate_antennas(
            cls,
            eval_query: str,
            ctrl: GameStateController,
            embedding_engine: EmbeddingEngine,
            active_entity_id: Optional[str] = None,
            active_entity_name: Optional[str] = None,
    ) -> Tuple[Optional[RagEvaluationProjection], Optional[str], Dict[str, float]]:
        """Calcula similitud vectorial, deduce la coincidencia ganadora y proyecta métricas RAG."""
        if not eval_query:
            return None, None, {}

        query_vec = embedding_engine.embed_text(eval_query)
        active_ids = {b.get("id") for b in ctrl.game_state.loreblocks.active}
        {b.get("id") for b in ctrl.game_state.loreblocks.done}

        candidates: List[Dict[str, Any]] = []
        scores_cache: Dict[str, float] = {}

        # 1. Antenas de bloques unknown (active_conditions)
        cls._collect_candidates(
            blocks=list(ctrl.game_state.loreblocks.unknown),
            condition_key="active_conditions",
            check_accessible=lambda pid: not pid or pid in active_ids,
            ctrl=ctrl,
            query_vec=query_vec,
            scores_cache=scores_cache,
            embedding_engine=embedding_engine,
            active_entity_id=active_entity_id,
            candidates=candidates,
        )

        # 2. Antenas de bloques active (active_conditions para reactivación de directivas RAG)
        cls._collect_candidates(
            blocks=list(ctrl.game_state.loreblocks.active),
            condition_key="active_conditions",
            check_accessible=lambda pid: True,
            ctrl=ctrl,
            query_vec=query_vec,
            scores_cache=scores_cache,
            embedding_engine=embedding_engine,
            active_entity_id=active_entity_id,
            candidates=candidates,
        )

        # 3. Antenas de bloques active (done_conditions)
        cls._collect_candidates(
            blocks=list(ctrl.game_state.loreblocks.active),
            condition_key="done_conditions",
            check_accessible=lambda pid: True,
            ctrl=ctrl,
            query_vec=query_vec,
            scores_cache=scores_cache,
            embedding_engine=embedding_engine,
            active_entity_id=active_entity_id,
            candidates=candidates,
        )

        if not candidates:
            return None, None, scores_cache

        # Deduplicar conservando el mejor resultado para cada par (lore_id, antenna)
        dedup_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for r in candidates:
            key = (r["lore_id"], r["antenna"])
            if key not in dedup_map:
                dedup_map[key] = r
            else:
                existing = dedup_map[key]
                ex_prio = (1 if existing["is_matched"] else 0, 1 if existing["conditions_met"] else 0,
                           existing["score"])
                new_prio = (1 if r["is_matched"] else 0, 1 if r["conditions_met"] else 0, r["score"])
                if new_prio > ex_prio:
                    dedup_map[key] = r

        unique_candidates = list(dedup_map.values())
        matching_candidates = [r for r in unique_candidates if r["is_matched"]]

        matched_lore_id: Optional[str] = None
        matched_antenna: Optional[str] = None
        injected_directive: Optional[str] = None

        if matching_candidates:
            # Orden de prioridad:
            # 1. Afecta a la entidad activa (boost)
            # 2. Especificidad ponderada (score + num_conditions * 0.04)
            # 3. Puntuación pura (score)
            def sort_key(cand: Dict[str, Any]) -> Tuple[int, float, float]:
                entity_boost = 1 if (active_entity_id and cand["affects_active_entity"]) else 0
                weighted = cand["score"] + (cand["num_conditions"] * 0.04)
                return entity_boost, weighted, cand["score"]

            matching_candidates.sort(key=sort_key, reverse=True)
            winner = matching_candidates[0]
            winner["is_injected"] = True

            matched_lore_id = winner["lore_id"]
            matched_antenna = winner["antenna"]

        # Construir DTO de proyección para UI / Debugger
        antenna_projections = [
            RagAntennaScoreProjection(
                antenna=r["antenna"],
                lore_id=r["lore_id"],
                lore_title=r["lore_title"],
                score=r["score"],
                threshold=r["threshold"],
                conditions_met=r["conditions_met"],
                is_matched=r["is_matched"],
                is_injected=r["is_injected"],
                affects_active_entity=r["affects_active_entity"],
            )
            for r in unique_candidates
        ]

        rag_evaluation = RagEvaluationProjection(
            player_input=eval_query,
            threshold=0.65,
            matched_lore_id=matched_lore_id,
            matched_antenna=matched_antenna,
            injected_directive=None,
            active_entity_id=active_entity_id,
            active_entity_name=active_entity_name,
            antennas=antenna_projections,
        )

        return rag_evaluation, None, scores_cache


    @classmethod
    def _collect_candidates(
            cls,
            blocks: List[Dict[str, Any]],
            condition_key: str,
            check_accessible: Any,
            ctrl: GameStateController,
            query_vec: Any,
            scores_cache: Dict[str, float],
            embedding_engine: EmbeddingEngine,
            active_entity_id: Optional[str],
            candidates: List[Dict[str, Any]],
    ) -> None:
        """Recolecta antenas de una colección de bloques sin duplicar código."""
        for blk in blocks:
            parent_id = blk.get("parent_id")
            is_accessible = check_accessible(parent_id)
            lore_id = blk.get("id", "")
            lore_title = blk.get("title") or blk.get("name") or lore_id
            blk_threshold = float(blk.get("threshold", 0.65))
            affects_active = LoreStateMachine.block_affects_entity(blk, active_entity_id)

            # 1. Antenas dentro de grupos de condiciones
            for grp in blk.get(condition_key, []) or []:
                grp_dict = grp if isinstance(grp, dict) else (grp.model_dump() if hasattr(grp, "model_dump") else {})
                if not grp_dict.get("rag_enabled"):
                    continue
                phrases = grp_dict.get("trigger_phrases", []) or []
                if not phrases:
                    continue

                grp_threshold = float(grp_dict.get("threshold") or blk_threshold)

                # Evaluar condiciones lógicas no-RAG del grupo
                non_rag_conditions = grp_dict.get("conditions", []) or []
                non_rag_met = True
                conds_met_count = 0
                for c in non_rag_conditions:
                    c_dict = c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else {})
                    met = LoreConditionEvaluator.is_single_condition_met(c_dict, ctrl)
                    if c_dict.get("is_negated"):
                        met = not met
                    if not met:
                        non_rag_met = False
                        break
                    conds_met_count += 1

                conditions_met = is_accessible and non_rag_met

                for phrase in phrases:
                    if not phrase:
                        continue
                    score = cls._get_or_compute_score(phrase, query_vec, scores_cache, embedding_engine)
                    is_matched = (score >= grp_threshold) and conditions_met
                    candidates.append({
                        "antenna": phrase,
                        "lore_id": lore_id,
                        "lore_title": lore_title,
                        "score": round(score, 4),
                        "threshold": grp_threshold,
                        "conditions_met": conditions_met,
                        "is_matched": is_matched,
                        "is_injected": False,
                        "affects_active_entity": affects_active,
                        "block": blk,
                        "num_conditions": conds_met_count,
                    })

            # 2. Antenas en la raíz del bloque
            for phrase in (blk.get("trigger_phrases", []) or []):
                if not phrase:
                    continue
                score = cls._get_or_compute_score(phrase, query_vec, scores_cache, embedding_engine)
                is_matched = (score >= blk_threshold) and is_accessible
                candidates.append({
                    "antenna": phrase,
                    "lore_id": lore_id,
                    "lore_title": lore_title,
                    "score": round(score, 4),
                    "threshold": blk_threshold,
                    "conditions_met": is_accessible,
                    "is_matched": is_matched,
                    "is_injected": False,
                    "affects_active_entity": affects_active,
                    "block": blk,
                    "num_conditions": 0,
                })

    @staticmethod
    def _get_or_compute_score(
            phrase: str,
            query_vec: Any,
            scores_cache: Dict[str, float],
            embedding_engine: EmbeddingEngine,
    ) -> float:
        if phrase in scores_cache:
            return scores_cache[phrase]
        p_vec = embedding_engine.embed_text(phrase)
        score = float(embedding_engine.compute_similarity(query_vec, p_vec))
        scores_cache[phrase] = score
        return score

