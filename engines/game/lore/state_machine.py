"""Máquina de Estados Jerárquica de LoreBlocks (HSM) y orquestación de ciclo."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from engines.embedding import EmbeddingEngine
from engines.game.lore.condition_evaluator import LoreConditionEvaluator
from engines.game.lore.effect_applier import LoreEffectApplier
from engines.game.state_controller import GameStateController


@dataclass
class HsmCycleResult:
    """Resultado del ciclo de evaluación de la máquina de estados HSM."""

    autonomous_push_actions: List[Tuple[str, str]] = field(default_factory=list)
    popup_title: Optional[str] = None
    popup_message: Optional[str] = None
    bypass_llm: bool = False
    bypass_text: Optional[str] = None
    bypass_author: Optional[str] = None
    injected_directive: Optional[str] = None


class LoreStateMachine:
    """Ejecutor de la máquina de estados de LoreBlocks con cascada jerárquica determinista."""

    MAX_CONVERGENCE_STEPS: int = 5

    @classmethod
    def execute_cycle(
        cls,
        ctrl: GameStateController,
        eval_query: str = "",
        precomputed_scores: Optional[Dict[str, float]] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        active_entity_id: Optional[str] = None,
        current_injected_directive: Optional[str] = None,
    ) -> HsmCycleResult:
        """Ejecuta iteraciones en bucle hasta que ningún estado cambie o se alcance el límite."""
        res = HsmCycleResult(injected_directive=current_injected_directive)

        for _ in range(cls.MAX_CONVERGENCE_STEPS):
            state_changed = False
            active_ids = {b.get("id") for b in ctrl.game_state.loreblocks.active}
            done_ids = {b.get("id") for b in ctrl.game_state.loreblocks.done}

            # -----------------------------------------------------------------
            # 1. Transición unknown -> active
            # -----------------------------------------------------------------
            unknown_to_activate = []
            for blk in list(ctrl.game_state.loreblocks.unknown):
                parent_id = blk.get("parent_id")
                is_accessible = not parent_id or parent_id in active_ids or parent_id in done_ids
                if not is_accessible:
                    continue

                active_conds = blk.get("active_conditions", [])
                has_conds = LoreConditionEvaluator.has_effective_active_conditions(blk)
                if not has_conds:
                    can_activate = True
                else:
                    can_activate = LoreConditionEvaluator.are_condition_groups_met(
                        active_conds,
                        ctrl,
                        eval_query=eval_query,
                        precomputed_scores=precomputed_scores,
                        embedding_engine=embedding_engine,
                    )

                if can_activate:
                    unknown_to_activate.append(blk)

            for blk in unknown_to_activate:
                if blk in ctrl.game_state.loreblocks.unknown:
                    ctrl.game_state.loreblocks.unknown.remove(blk)

                # Tratamiento de tipo popup: aviso modal directo sin efectos ni interrupción de turno
                if blk.get("type") == "popup":
                    blk["state"] = "done"
                    ctrl.game_state.loreblocks.done.append(blk)
                    state_changed = True
                    res.popup_title = blk.get("title") or blk.get("name", "Aviso del Sistema")
                    res.popup_message = (
                        blk.get("description")
                        or (blk.get("effects", [{}])[0].get("directive") if blk.get("effects") else "")
                        or blk.get("name", "")
                    )
                    continue

                blk["state"] = "active"
                ctrl.game_state.loreblocks.active.append(blk)
                state_changed = True

                # Bloques sin done_conditions efectivas o Capítulos aplican efectos al activarse
                if not LoreConditionEvaluator.has_effective_done_conditions(blk) or blk.get("type") == "Chapter":
                    LoreEffectApplier.apply_effects(blk.get("effects", []), ctrl, res.autonomous_push_actions)
                    cls._check_bypass(blk, ctrl, res)

            # -----------------------------------------------------------------
            # 2. Transición active -> done
            # -----------------------------------------------------------------
            active_to_complete = []
            for blk in list(ctrl.game_state.loreblocks.active):
                done_conds = blk.get("done_conditions", [])
                if LoreConditionEvaluator.has_effective_done_conditions(blk) and LoreConditionEvaluator.are_condition_groups_met(
                    done_conds,
                    ctrl,
                    eval_query=eval_query,
                    precomputed_scores=precomputed_scores,
                    embedding_engine=embedding_engine,
                ):
                    active_to_complete.append(blk)

            for blk in active_to_complete:
                if blk in ctrl.game_state.loreblocks.active:
                    ctrl.game_state.loreblocks.active.remove(blk)
                blk["state"] = "done"
                ctrl.game_state.loreblocks.done.append(blk)
                state_changed = True

                if blk.get("type") == "popup":
                    res.popup_title = blk.get("title") or blk.get("name", "Aviso del Sistema")
                    res.popup_message = (
                        blk.get("description")
                        or (blk.get("effects", [{}])[0].get("directive") if blk.get("effects") else "")
                        or blk.get("name", "")
                    )
                    continue

                LoreEffectApplier.apply_effects(blk.get("effects", []), ctrl, res.autonomous_push_actions)
                cls._check_bypass(blk, ctrl, res)

            if not state_changed:
                break

        # Sincronizar cuaderno de misiones tras la convergencia
        ctrl.sync_notebook()

        # Inyección de directiva de hook pasivo si no había directiva RAG previa
        if not res.injected_directive and active_entity_id:
            res.injected_directive = cls._resolve_hook_directive(ctrl, active_entity_id)

        return res

    @classmethod
    def _check_bypass(cls, blk: Dict[str, Any], ctrl: GameStateController, res: HsmCycleResult) -> None:
        for eff in blk.get("effects", []):
            if isinstance(eff, dict) and eff.get("bypass_llm"):
                res.bypass_llm = True
                res.bypass_text = eff.get("directive")
                tgt = eff.get("target")
                if tgt and tgt in ctrl.npcs_by_id:
                    res.bypass_author = ctrl.npcs_by_id[tgt].name

    @classmethod
    def _resolve_hook_directive(cls, ctrl: GameStateController, active_entity_id: str) -> Optional[str]:
        """Busca directivas de hook en bloques activos hacia la entidad activa."""
        for blk in ctrl.game_state.loreblocks.active:
            for eff in blk.get("effects", []):
                if isinstance(eff, dict) and eff.get("action") == "hook" and eff.get("target") == active_entity_id:
                    if eff.get("directive") and not (eff.get("give_items") or eff.get("take_items")):
                        return eff.get("directive")
            if blk.get("directive") and cls.block_affects_entity(blk, active_entity_id):
                return blk.get("directive")
        return None

    @classmethod
    def block_affects_entity(cls, blk: Dict[str, Any], entity_id: Optional[str]) -> bool:
        """Determina si un LoreBlock referencia o afecta directamente a la entidad objetivo del turno."""
        if not entity_id:
            return False

        for g_key in ("active_conditions", "done_conditions"):
            for grp in blk.get(g_key, []) or []:
                conditions = grp.get("conditions", []) if isinstance(grp, dict) else getattr(grp, "conditions", [])
                for c in conditions:
                    c_dict = c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else {})
                    if c_dict.get("entity_id") == entity_id or c_dict.get("value") == entity_id:
                        return True

        for eff in blk.get("effects", []) or []:
            if not isinstance(eff, dict):
                continue
            if eff.get("target") == entity_id:
                return True
            if entity_id in eff.get("unlock_places", []) or entity_id in eff.get("block_places", []):
                return True
            if entity_id in eff.get("unlock_npcs", []) or entity_id in eff.get("unlock_items", []):
                return True

        return False
