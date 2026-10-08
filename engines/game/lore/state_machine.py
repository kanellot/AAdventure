"""Máquina de Estados Jerárquica de LoreBlocks (HSM) y orquestación de ciclo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engines.embedding import EmbeddingEngine
from engines.game.lore.condition_evaluator import LoreConditionEvaluator
from engines.game.lore.effect_applier import AutonomousPushAction, LoreEffectApplier
from engines.game.lore.hooks import HookResolver
from engines.game.lore.library import LoreLibrary
from engines.game.state_controller import GameStateController


@dataclass
class HsmCycleResult:
    """Resultado del ciclo de evaluación de la máquina de estados HSM."""

    autonomous_push_actions: List[AutonomousPushAction] = field(default_factory=list)
    popups: List[Tuple[str, str]] = field(default_factory=list)
    popup_title: Optional[str] = None
    popup_message: Optional[str] = None
    bypass_llm: bool = False
    bypass_text: Optional[str] = None
    bypass_author: Optional[str] = None
    injected_directive: Optional[str] = None


class LoreStateMachine:
    """Ejecutor de la máquina de estados de LoreBlocks con soporte bidireccional y doble modo."""

    @classmethod
    def execute_turn_0_cycle(cls, ctrl: GameStateController) -> HsmCycleResult:
        """Ejecuta el ciclo inicial del Turno 0: segrega popups, evalúa popups iniciales y activa misiones iniciales."""
        res = HsmCycleResult()

        # 1. Segregación de popups
        popups_to_move = [b for b in list(ctrl.game_state.loreblocks.unknown) if b.get("type") == "popup"]
        for b in popups_to_move:
            ctrl.game_state.loreblocks.unknown.remove(b)
            ctrl.game_state.loreblocks.popups.append(b)

        # 2. Evaluación de popups iniciales
        triggered_popups = LoreConditionEvaluator.check_block_conditions(
            list(ctrl.game_state.loreblocks.popups),
            phase="active",
            ctrl=ctrl,
            require_parent_accessible=False,
        )
        for blk in triggered_popups:
            if blk in ctrl.game_state.loreblocks.popups:
                ctrl.game_state.loreblocks.popups.remove(blk)
            blk["state"] = "done"
            ctrl.game_state.loreblocks.done.append(blk)
            title = blk.get("title") or blk.get("name", "Aviso del Sistema")
            message = blk.get("description") or blk.get("name", "")
            res.popups.append((title, message))
            if not res.popup_message:
                res.popup_title = title
                res.popup_message = message

        # 3. Activación inicial de bloques raíz o sin condiciones previas (en cascada)
        changed = True
        while changed:
            changed = False
            active_ids = {b.get("id") for b in ctrl.game_state.loreblocks.active}
            for blk in list(ctrl.game_state.loreblocks.unknown):
                parent_id = blk.get("parent_id")
                if parent_id and parent_id not in active_ids:
                    continue
                if not LoreConditionEvaluator.has_effective_active_conditions(blk):
                    ctrl.game_state.loreblocks.unknown.remove(blk)
                    blk["state"] = "active"
                    ctrl.game_state.loreblocks.active.append(blk)
                    LoreEffectApplier.apply_block_effects([blk], "active", ctrl, res.autonomous_push_actions)
                    changed = True

        ctrl.sync_notebook()
        return res

    @classmethod
    def execute_cycle(
            cls,
            ctrl: GameStateController,
            eval_query: str = "",
            precomputed_scores: Optional[Dict[str, float]] = None,
            embedding_engine: Optional[EmbeddingEngine] = None,
            active_entity_id: Optional[str] = None,
            current_injected_directive: Optional[str] = None,
            action_name: str = "",
            source: str = "PLAYER",
    ) -> HsmCycleResult:
        """Ejecuta el pipeline secuencial determinista de LoreBlocks en cada turno."""
        res = HsmCycleResult(injected_directive=current_injected_directive)
        transition_hooks: List[Tuple[str, Dict[str, Any]]] = []

        # ---------------------------------------------------------------------
        # PASO 1: POPUPS
        # ---------------------------------------------------------------------
        for blk in list(ctrl.game_state.loreblocks.unknown):
            if blk.get("type") == "popup":
                ctrl.game_state.loreblocks.unknown.remove(blk)
                ctrl.game_state.loreblocks.popups.append(blk)

        triggered_popups = LoreConditionEvaluator.check_block_conditions(
            list(ctrl.game_state.loreblocks.popups),
            phase="active",
            ctrl=ctrl,
            eval_query=eval_query,
            precomputed_scores=precomputed_scores,
            embedding_engine=embedding_engine,
            require_parent_accessible=False,
        )
        for blk in triggered_popups:
            if blk in ctrl.game_state.loreblocks.popups:
                ctrl.game_state.loreblocks.popups.remove(blk)
            blk["state"] = "done"
            ctrl.game_state.loreblocks.done.append(blk)
            title = blk.get("title") or blk.get("name", "Aviso del Sistema")
            message = blk.get("description") or blk.get("name", "")
            res.popups.append((title, message))
            if not res.popup_message:
                res.popup_title = title
                res.popup_message = message

        # ---------------------------------------------------------------------
        # PASO 2: REVERSIÓN DE ACTIVE A UNKNOWN (SOLO EVENTOS)
        # ---------------------------------------------------------------------
        # Chapter, Quest y Task solo progresan hacia adelante para no corromper el notebook.
        for blk in list(ctrl.game_state.loreblocks.active):
            if blk.get("type") == "Event" and LoreConditionEvaluator.has_effective_active_conditions(blk):
                is_still_met = LoreConditionEvaluator.is_block_condition_met(
                    blk,
                    phase="active",
                    ctrl=ctrl,
                    eval_query=eval_query,
                    precomputed_scores=precomputed_scores,
                    embedding_engine=embedding_engine,
                    require_parent_accessible=False,
                    ignore_rag=True,  # Ignora RAG para que no oscile por cambios en el input del jugador
                )
                if not is_still_met:
                    ctrl.game_state.loreblocks.active.remove(blk)
                    blk["state"] = "unknown"
                    ctrl.game_state.loreblocks.unknown.append(blk)

        # ---------------------------------------------------------------------
        # BUCLE DE CONVERGENCIA EN CASCADA (Pasos 3, 4 y 5)
        # ---------------------------------------------------------------------
        MAX_CONVERGENCE_STEPS = 5
        newly_activated_all = set()

        for iteration in range(MAX_CONVERGENCE_STEPS):
            state_changed = False

            # PASO 3: ACTIVACIÓN UNKNOWN A ACTIVE
            active_ids = {b.get("id") for b in ctrl.game_state.loreblocks.active}
            step_eval_query = eval_query if iteration == 0 else ""
            for blk in list(ctrl.game_state.loreblocks.unknown):
                parent_id = blk.get("parent_id")
                if parent_id and parent_id not in active_ids:
                    continue
                if LoreConditionEvaluator.is_block_condition_met(
                    blk,
                    phase="active",
                    ctrl=ctrl,
                    eval_query=step_eval_query,
                    precomputed_scores=precomputed_scores,
                    embedding_engine=embedding_engine,
                    require_parent_accessible=False,
                ):
                    ctrl.game_state.loreblocks.unknown.remove(blk)
                    blk["state"] = "active"
                    ctrl.game_state.loreblocks.active.append(blk)
                    bid = blk.get("id", "")
                    newly_activated_all.add(bid)
                    state_changed = True

                    # Recolectar hooks de transición activados en este turno
                    effs = blk.get("active_effects", []) or blk.get("effects", []) or []
                    for eff in effs:
                        if isinstance(eff, dict) and eff.get("action", "hook") == "hook":
                            transition_hooks.append((bid, eff))

                    # Aplicar active_effects de inmediato al activarse
                    LoreEffectApplier.apply_block_effects([blk], "active", ctrl, res.autonomous_push_actions)

            # PASO 4: TRANSICIÓN ACTIVE A DONE (done_buffer)
            done_ids = {b.get("id") for b in ctrl.game_state.loreblocks.done}
            done_buffer: List[Dict[str, Any]] = []

            for blk in list(ctrl.game_state.loreblocks.active):
                parent_id = blk.get("parent_id")
                can_done = False
                if parent_id and parent_id in done_ids:
                    can_done = True
                elif LoreConditionEvaluator.has_effective_done_conditions(blk):
                    # Aislamiento conversacional: bloques recién activados en cascada no consumen el input
                    block_eval_query = "" if blk.get("id") in newly_activated_all else eval_query
                    if LoreConditionEvaluator.is_block_condition_met(
                        blk,
                        phase="done",
                        ctrl=ctrl,
                        eval_query=block_eval_query,
                        precomputed_scores=precomputed_scores,
                        embedding_engine=embedding_engine,
                    ):
                        can_done = True

                if can_done:
                    ctrl.game_state.loreblocks.active.remove(blk)
                    blk["state"] = "done"
                    ctrl.game_state.loreblocks.done.append(blk)
                    done_buffer.append(blk)
                    state_changed = True

            # PASO 5: APLICACIÓN DE EFECTOS DONE
            if done_buffer:
                for blk in done_buffer:
                    bid = blk.get("id", "")
                    for eff in (blk.get("done_effects", []) or []):
                        if isinstance(eff, dict) and eff.get("action") == "hook":
                            transition_hooks.append((bid, eff))
                LoreEffectApplier.apply_block_effects(done_buffer, "done", ctrl, res.autonomous_push_actions)

            if not state_changed:
                break

        # ---------------------------------------------------------------------
        # PASO 6: POPUPS POST-CONVERGENCIA
        # ---------------------------------------------------------------------
        triggered_popups_post = LoreConditionEvaluator.check_block_conditions(
            list(ctrl.game_state.loreblocks.popups),
            phase="active",
            ctrl=ctrl,
            eval_query=eval_query,
            precomputed_scores=precomputed_scores,
            embedding_engine=embedding_engine,
            require_parent_accessible=False,
        )
        for blk in triggered_popups_post:
            if blk in ctrl.game_state.loreblocks.popups:
                ctrl.game_state.loreblocks.popups.remove(blk)
            blk["state"] = "done"
            ctrl.game_state.loreblocks.done.append(blk)
            title = blk.get("title") or blk.get("name", "Aviso del Sistema")
            message = blk.get("description") or blk.get("name", "")
            res.popups.append((title, message))
            if not res.popup_message:
                res.popup_title = title
                res.popup_message = message

        # ---------------------------------------------------------------------
        # PASO 7: FINALIZACIÓN, SINCRONIZACIÓN Y HOOK RESOLUTION
        # ---------------------------------------------------------------------
        ctrl.sync_notebook()

        if source == "PLAYER" and active_entity_id and action_name in ("LOOK", "TALK"):
            # Recolectar hooks armados de bloques actualmente activos
            armed_hooks: List[Tuple[str, Dict[str, Any]]] = []
            for blk in ctrl.game_state.loreblocks.active:
                bid = blk.get("id", "")
                effs = blk.get("active_effects", []) or blk.get("effects", []) or []

                is_rag_gated = LoreConditionEvaluator.has_rag_conditions(blk, phase="active")

                if is_rag_gated:
                    # Un bloque RAG solo dispara su hook en el turno en que se cumple dicha antena
                    if not eval_query:
                        continue
                    if LoreConditionEvaluator.is_block_condition_met(
                        blk,
                        phase="active",
                        ctrl=ctrl,
                        eval_query=eval_query,
                        precomputed_scores=precomputed_scores,
                        embedding_engine=embedding_engine,
                        require_parent_accessible=False,
                        ignore_rag=False,
                    ):
                        for eff in effs:
                            if isinstance(eff, dict) and eff.get("action", "hook") == "hook":
                                if (bid, eff) not in transition_hooks:
                                    transition_hooks.append((bid, eff))
                else:
                    # Bloque no-RAG: hook persistente/ambiental en armed_hooks
                    for eff in effs:
                        if isinstance(eff, dict) and eff.get("action", "hook") == "hook":
                            armed_hooks.append((bid, eff))

            library = getattr(ctrl, "lore_library", None) or LoreLibrary(
                list(ctrl.game_state.loreblocks.active)
                + list(ctrl.game_state.loreblocks.unknown)
                + list(ctrl.game_state.loreblocks.done)
                + list(ctrl.game_state.loreblocks.popups)
            )

            resolved = HookResolver.resolve_hook(
                transition_hooks=transition_hooks,
                armed_hooks=armed_hooks,
                active_entity_id=active_entity_id,
                action_name=action_name,
                library=library,
                ctrl=ctrl,
            )

            if resolved:
                if resolved.bypass_llm:
                    res.bypass_llm = True
                    res.bypass_text = resolved.directive
                    res.bypass_author = resolved.bypass_author
                else:
                    res.injected_directive = resolved.directive

        return res

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

        all_effects = (
            (blk.get("active_effects", []) or [])
            + (blk.get("done_effects", []) or [])
            + (blk.get("effects", []) or [])
        )
        for eff in all_effects:
            if not isinstance(eff, dict):
                continue
            if eff.get("target") == entity_id:
                return True
            if entity_id in eff.get("unlock_places", []) or entity_id in eff.get("block_places", []):
                return True
            if entity_id in eff.get("unlock_npcs", []) or entity_id in eff.get("unlock_items", []):
                return True

        return False
