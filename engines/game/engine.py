"""Motor principal de juego (GameEngine): orquestador de ciclo de vida y turnos deterministas."""

from __future__ import annotations
import logging
import os
import queue
import sys
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple

from domains.projections import (
    AvailableActionsProjection,
    GameStateProjection,
    InventoryProjection,
    LoreGraphProjection,
    NotebookProjection,
    RagEvaluationProjection,
    TurnOutput,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
    WorldMapProjection,
)
from engines.events import EngineEventListener, EngineTask
from engines.game.actions import DialogueAction, LookAction, MoveAction
from engines.game.lore import (
    HsmCycleResult,
    LoreConditionEvaluator,
    LoreEffectApplier,
    LoreStateMachine,
)
from engines.game.projections import ProjectionAssembler
from engines.game.rag import RagAntennaEvaluator
from engines.game.rules_validator import ActionValidationResult, RulesValidator
from engines.game.state_controller import GameStateController
from engines.game.utils import TimeCalculator
from engines.game.worker import EngineWorker
from engines.transformer import TransformerEngine
from engines.embedding import EmbeddingEngine, EmbeddingFactory, MockEmbeddingBackend

logger = logging.getLogger(__name__)


class GameEngine:
    """Orquestador de turnos deterministas y fachada del motor de juego."""

    MAX_AUTONOMOUS_CHAIN_DEPTH: int = 3
    MAX_CONVERSATION_MESSAGES: int = 16
    DIALOGUE_ELAPSED_MINUTES: int = 2
    BASE_TRAVEL_SPEED: float = 4.5

    def __init__(
        self,
        game_state_controller: Optional[GameStateController] = None,
        transformer_engine: Optional[TransformerEngine] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        listeners: Optional[List[EngineEventListener]] = None,
        aad_path: Optional[str] = None,
        world_json_path: Optional[str] = None,
    ):
        path = aad_path or world_json_path
        if game_state_controller is None:
            if path:
                game_state_controller = GameStateController.from_aad(path)
            else:
                raise ValueError("Se requiere game_state_controller o aad_path para inicializar GameEngine.")

        self.game_state_controller = game_state_controller

        # Detección de entorno de prueba para Mock
        is_test_mode = bool(
            os.environ.get("TESTING")
            or (
                "unittest" in sys.modules
                and not any(arg.endswith("main.py") or "main.py" in arg for arg in sys.argv)
            )
        )

        # Inicialización de TransformerEngine
        if transformer_engine is None and path is not None:
            if is_test_mode:
                from engines.transformer.mock_adapter import MockLLMAdapter
                transformer_engine = TransformerEngine(llm_adapter=MockLLMAdapter())
            else:
                try:
                    from engines.transformer.factory import create_llm_adapter
                    adapter = create_llm_adapter()
                    transformer_engine = TransformerEngine(llm_adapter=adapter)
                except Exception as e:
                    logger.warning("Fallo al inicializar adaptador LLM real (%s). Usando MockLLMAdapter.", e)
                    from engines.transformer.mock_adapter import MockLLMAdapter
                    transformer_engine = TransformerEngine(llm_adapter=MockLLMAdapter())

        self.transformer_engine = transformer_engine

        # Inicialización de EmbeddingEngine
        if embedding_engine is None:
            if is_test_mode:
                self.embedding_engine = EmbeddingEngine(backend=MockEmbeddingBackend())
            else:
                try:
                    backend = EmbeddingFactory.get_backend()
                    self.embedding_engine = EmbeddingEngine(backend=backend)
                except Exception as e:
                    logger.warning("Fallo al inicializar EmbeddingEngine real (%s). Usando MockEmbeddingBackend.", e)
                    self.embedding_engine = EmbeddingEngine(backend=MockEmbeddingBackend())
        else:
            self.embedding_engine = embedding_engine

        # Componente de concurrencia y worker en segundo plano
        self.worker = EngineWorker(
            turn_executor=self._execute_worker_task,
            ui_state_provider=self.get_ui_state_projection,
            listeners=listeners,
        )

    # =========================================================================
    # Propiedades y Acceso Concurrente
    # =========================================================================

    @property
    def listeners(self) -> List[EngineEventListener]:
        return self.worker.listeners

    @listeners.setter
    def listeners(self, val: List[EngineEventListener]) -> None:
        self.worker.listeners = list(val or [])

    @property
    def task_queue(self) -> queue.Queue[EngineTask]:
        return self.worker.task_queue

    @property
    def worker_thread(self) -> Optional[threading.Thread]:
        return self.worker.worker_thread

    @property
    def _running(self) -> bool:
        return self.worker._running

    @_running.setter
    def _running(self, val: bool) -> None:
        self.worker._running = val

    def start(self) -> None:
        """Inicia el worker en segundo plano."""
        self.worker.start()

    def stop(self) -> None:
        """Detiene el bucle de trabajo de forma ordenada."""
        self.worker.stop()

    def add_listener(self, listener: EngineEventListener) -> None:
        self.worker.add_listener(listener)

    def remove_listener(self, listener: EngineEventListener) -> None:
        self.worker.remove_listener(listener)

    def notify_thinking(self, is_thinking: bool, task_id: str = "", action: str = "", target: str = "", source: str = "PLAYER") -> None:
        self.worker.notify_thinking(is_thinking, task_id=task_id, action=action, target=target, source=source)

    def notify_turn_completed(self, turn_result: TurnResultProjection, task_id: str = "") -> None:
        self.worker.notify_turn_completed(turn_result, task_id=task_id)

    # =========================================================================
    # Métodos de Entrada de la UI (Encolamiento)
    # =========================================================================

    def enqueue_action(self, action: str = "", target: str = "", player_input: str = "") -> str:
        """Encola una acción o input enviada por el jugador, notificando thinking síncronamente."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.notify_thinking(
            is_thinking=True,
            task_id=task_id,
            action=action,
            target=target,
            source="PLAYER",
        )
        self.worker.task_queue.put(
            EngineTask(
                task_id=task_id,
                action=action,
                target=target,
                player_input=player_input,
                source="PLAYER",
            )
        )
        return task_id

    def enqueue_message(self, text: str) -> str:
        """Encola texto libre del jugador."""
        return self.enqueue_action(action="", target="", player_input=text)

    def enqueue_start_game(self) -> str:
        """Encola el Turno 0 para iniciar formalmente la partida."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.notify_thinking(
            is_thinking=True,
            task_id=task_id,
            action="START",
            target="",
            source="PLAYER",
        )
        self.worker.task_queue.put(
            EngineTask(
                task_id=task_id,
                action="__START__",
                target="",
                player_input="",
                source="PLAYER",
            )
        )
        return task_id

    def _execute_worker_task(self, task: EngineTask) -> TurnResultProjection:
        """Despacha la tarea al método de turno correspondiente."""
        if task.action == "__START__":
            return self.execute_turn_0()
        return self.execute_turn(
            action=task.action,
            target=task.target,
            player_input=task.player_input,
        )

    # =========================================================================
    # Pipeline Determinista de Turno (Turno 0 y 5 Fases)
    # =========================================================================

    def execute_turn_0(self) -> TurnResultProjection:
        """Ejecuta el Turno 0 de inicio de partida (texto Dungeon Master y popups iniciales)."""
        ctrl = self.game_state_controller
        start_loc = ctrl.game_state.current_location

        ctrl.set_player_state("EXPLORE")
        ctrl.set_player_target(None)

        # Evaluación de Pop-ups iniciales
        popup_title: Optional[str] = None
        popup_message: Optional[str] = None

        for blk in list(ctrl.game_state.loreblocks.unknown):
            if blk.get("type") == "popup":
                active_conds = blk.get("active_conditions", [])
                has_conds = LoreConditionEvaluator.has_effective_active_conditions(blk)
                if not has_conds or LoreConditionEvaluator.are_condition_groups_met(active_conds, ctrl, eval_query=""):
                    ctrl.game_state.loreblocks.unknown.remove(blk)
                    blk["state"] = "done"
                    ctrl.game_state.loreblocks.done.append(blk)
                    popup_title = blk.get("title") or blk.get("name", "Aviso del Sistema")
                    popup_message = (
                        blk.get("description")
                        or (blk.get("effects", [{}])[0].get("directive") if blk.get("effects") else "")
                        or blk.get("name", "")
                    )

        ctrl.sync_notebook()

        # Obtención del texto introductorio
        intro_text = (getattr(ctrl.world, "initial_text", "") or "").strip()
        if not intro_text:
            current_place = ctrl.places_by_id.get(start_loc)
            if current_place and current_place.description:
                intro_text = f"Te encuentras en {current_place.name}. {current_place.description}"
            else:
                intro_text = "Tu aventura comienza aquí."

        output = TurnOutput(
            author="Dungeon Master",
            type="msg",
            msg=intro_text,
            player_state="EXPLORE",
            popup_title=popup_title,
            popup_message=popup_message,
        )

        return ProjectionAssembler.build_turn_result(output, ctrl)

    def execute_turn(
        self,
        action: str,
        target: Optional[str] = None,
        player_input: str = "",
        autonomous_depth: int = 0,
    ) -> TurnResultProjection:
        """Ejecuta de forma síncrona el pipeline completo de 5 fases deterministas."""
        ctrl = self.game_state_controller

        # ---------------------------------------------------------------------
        # FASE 1: Verificación de Acción e Input Físico
        # ---------------------------------------------------------------------
        val_res = RulesValidator.validate(action, target, player_input, ctrl)
        if not val_res.is_valid:
            return ProjectionAssembler.build_turn_result(val_res.error_output, ctrl)

        action_name = val_res.action_name
        resolved_target = val_res.resolved_target

        # ---------------------------------------------------------------------
        # FASE 2: Mutación Canónica de Estado
        # ---------------------------------------------------------------------
        if action_name == "MOVE":
            ctrl.set_player_state("EXPLORE")
            ctrl.set_player_target(None)
            destination_place = val_res.traversed_places[-1]
            ctrl.set_current_location(destination_place.id)
            travel_minutes = TimeCalculator.calculate_travel_time(
                val_res.traversed_conns,
                travel_speed=self.BASE_TRAVEL_SPEED,
            )
            ctrl.add_elapsed_minutes(travel_minutes)

        elif action_name == "TALK":
            ctrl.set_player_state("TALK")
            ctrl.set_player_target(resolved_target)
            ctrl.add_elapsed_minutes(self.DIALOGUE_ELAPSED_MINUTES)

        elif action_name == "LOOK":
            ctrl.set_player_state("LOOK")
            ctrl.set_player_target(resolved_target)

        # Identificación de la entidad activa para sesgo RAG
        active_entity_id = (
            resolved_target
            if action_name in ("TALK", "LOOK")
            else (val_res.traversed_places[-1].id if action_name == "MOVE" and val_res.traversed_places else ctrl.game_state.current_location)
        )
        active_entity_name = (
            ctrl.npcs_by_id[active_entity_id].name
            if active_entity_id in ctrl.npcs_by_id
            else (ctrl.places_by_id[active_entity_id].name if active_entity_id in ctrl.places_by_id else active_entity_id)
        )

        # ---------------------------------------------------------------------
        # Evaluación Semántica RAG (Deduplicada)
        # ---------------------------------------------------------------------
        eval_query = player_input.strip() if player_input else ""
        rag_evaluation, injected_directive, precomputed_scores = RagAntennaEvaluator.evaluate_antennas(
            eval_query=eval_query,
            ctrl=ctrl,
            embedding_engine=self.embedding_engine,
            active_entity_id=active_entity_id,
            active_entity_name=active_entity_name,
        )

        # ---------------------------------------------------------------------
        # FASE 3: Máquina de Estados HSM y Ciclo en Cascada
        # ---------------------------------------------------------------------
        hsm_res: HsmCycleResult = LoreStateMachine.execute_cycle(
            ctrl=ctrl,
            eval_query=eval_query,
            precomputed_scores=precomputed_scores,
            embedding_engine=self.embedding_engine,
            active_entity_id=active_entity_id,
            current_injected_directive=injected_directive,
        )

        # ---------------------------------------------------------------------
        # FASE 4: Orquestación Narrativa
        # ---------------------------------------------------------------------
        if hsm_res.bypass_llm and hsm_res.bypass_text:
            output = TurnOutput(
                author=hsm_res.bypass_author or (
                    ctrl.npcs_by_id[resolved_target].name
                    if action_name == "TALK" and resolved_target in ctrl.npcs_by_id
                    else "Dungeon Master"
                ),
                type="msg",
                msg=hsm_res.bypass_text,
                player_state=ctrl.game_state.player_state,
            )
            prompt_text = None
        else:
            output, prompt_text = self._generate_narrative_output(
                action_name=action_name,
                target=resolved_target if action_name in ("TALK", "LOOK") else (target or ""),
                player_input=player_input,
                val_res=val_res,
                directive=hsm_res.injected_directive,
            )

        if hsm_res.popup_message:
            output.popup_message = hsm_res.popup_message
            output.popup_title = hsm_res.popup_title

        # ---------------------------------------------------------------------
        # FASE 5: Emisión de Proyección Consolidada y Encadenamiento Autónomo
        # ---------------------------------------------------------------------
        turn_result = ProjectionAssembler.build_turn_result(
            output=output,
            ctrl=ctrl,
            prompt_text=prompt_text,
            rag_eval=rag_evaluation,
        )

        if hsm_res.autonomous_push_actions and autonomous_depth < self.MAX_AUTONOMOUS_CHAIN_DEPTH:
            for push_act, push_tgt in hsm_res.autonomous_push_actions:
                self.execute_turn(
                    action=push_act,
                    target=push_tgt,
                    autonomous_depth=autonomous_depth + 1,
                )
        elif autonomous_depth >= self.MAX_AUTONOMOUS_CHAIN_DEPTH:
            logger.warning("Límite MAX_AUTONOMOUS_CHAIN_DEPTH alcanzado; bucle autónomo detenido de forma segura.")

        return turn_result

    def _generate_narrative_output(
        self,
        action_name: str,
        target: str,
        player_input: str,
        val_res: ActionValidationResult,
        directive: Optional[str] = None,
    ) -> Tuple[TurnOutput, Optional[str]]:
        """Invoca a las acciones desacopladas (MoveAction, DialogueAction, LookAction)."""
        ctrl = self.game_state_controller

        if action_name == "MOVE":
            origin = val_res.traversed_places[0] if val_res.traversed_places else ctrl.game_state.place
            dest = val_res.traversed_places[-1] if val_res.traversed_places else ctrl.game_state.place
            path_taken = val_res.traversed_places[1:-1] if len(val_res.traversed_places) > 2 else []
            travel_time = TimeCalculator.calculate_travel_time(val_res.traversed_conns, travel_speed=self.BASE_TRAVEL_SPEED)
            move_act = MoveAction(
                origin_place=origin,
                destination_place=dest,
                path_taken=path_taken,
                travel_time=travel_time,
                directive=directive,
                blocked_place=val_res.blocked_place_obstacle,
            )
            res = move_act.generate_narrative(ctrl, player_input, self.transformer_engine)
            return (
                TurnOutput(
                    author="Dungeon Master",
                    type="msg",
                    msg=res.msg,
                    player_state="EXPLORE",
                ),
                res.prompt,
            )

        elif action_name == "TALK":
            npc = ctrl.npcs_by_id.get(target)
            npc_name = npc.name if npc else target
            dialogue_act = DialogueAction(target_npc=target, directive=directive)
            res = dialogue_act.generate_narrative(ctrl, player_input, self.transformer_engine)
            if res.extra is not None:
                ctrl.update_npc_affinity(target, res.extra)

            ctrl.append_dialogue_exchange(
                target_id=target,
                player_msg=player_input,
                npc_name=npc_name,
                npc_msg=res.msg,
                max_messages=self.MAX_CONVERSATION_MESSAGES,
            )
            return (
                TurnOutput(
                    author=npc_name,
                    type="msg",
                    msg=res.msg,
                    player_state="TALK",
                ),
                res.prompt,
            )

        elif action_name == "LOOK":
            look_act = LookAction(target=target, directive=directive)
            res = look_act.generate_narrative(ctrl, player_input, self.transformer_engine)
            return (
                TurnOutput(
                    author="Dungeon Master",
                    type="msg",
                    msg=res.msg,
                    player_state="LOOK",
                ),
                res.prompt,
            )

        return (TurnOutput(author="SYSTEM", type="msg", msg="", player_state="EXPLORE"), None)

    # =========================================================================
    # Proyecciones DTO Públicas
    # =========================================================================

    def get_ui_state_projection(self) -> UIStateProjection:
        return ProjectionAssembler.build_ui_state_projection(self.game_state_controller)

    def get_available_actions_projection(self) -> AvailableActionsProjection:
        return ProjectionAssembler.build_available_actions_projection(self.game_state_controller)

    def get_navigation_hierarchy(self) -> WorldHierarchyProjection:
        return ProjectionAssembler.build_navigation_hierarchy(self.game_state_controller)

    def get_entities_hierarchy(self) -> WorldHierarchyProjection:
        return ProjectionAssembler.build_entities_hierarchy(self.game_state_controller)

    def get_lore_graph_projection(self) -> LoreGraphProjection:
        return ProjectionAssembler.build_lore_graph_projection(self.game_state_controller)

    def get_game_state_projection(self) -> GameStateProjection:
        return ProjectionAssembler.build_game_state_projection(self.game_state_controller, self.BASE_TRAVEL_SPEED)

    def get_world_map_projection(self) -> WorldMapProjection:
        return ProjectionAssembler.build_world_map_projection(self.game_state_controller)

    def get_inventory_projection(self) -> InventoryProjection:
        return ProjectionAssembler.build_inventory_projection(self.game_state_controller)

    def get_notebook_projection(self) -> NotebookProjection:
        return NotebookProjection(quests=list(self.game_state_controller.game_state.notebook))

    def get_player_name(self) -> str:
        return self.game_state_controller.game_state.player_name

    def get_world_name(self) -> str:
        return self.game_state_controller.world.name if self.game_state_controller.world else "Aventura"

    def get_all_target_names(self) -> List[str]:
        ctrl = self.game_state_controller
        names = set()
        for p in ctrl.places_by_id.values():
            names.add(p.name)
            names.add(p.id)
        for n in ctrl.npcs_by_id.values():
            names.add(n.name)
            names.add(n.id)
        for it in ctrl.items_by_id.values():
            names.add(it.name)
            names.add(it.id)
        return sorted(list(names))

    # =========================================================================
    # Shims Internos Limpios (Garantía de Cero Ruptura)
    # =========================================================================

    def _build_world_map_projection(self) -> WorldMapProjection:
        return self.get_world_map_projection()

    def _build_inventory_projection(self) -> InventoryProjection:
        return self.get_inventory_projection()

    def _assemble_turn_result(
        self,
        output: TurnOutput,
        prompt_text: Optional[str] = None,
        rag_eval: Optional[RagEvaluationProjection] = None,
        engine_result: Optional[str] = None,
    ) -> TurnResultProjection:
        return ProjectionAssembler.build_turn_result(output, self.game_state_controller, prompt_text=prompt_text, rag_eval=rag_eval)

    def _is_npc_at_location(self, npc_id: str, place_id: str) -> bool:
        return RulesValidator.is_npc_at_location(npc_id, place_id, self.game_state_controller)

    def _is_entity_reachable_to_look(self, entity_id: str, current_place_id: str) -> bool:
        return RulesValidator.is_entity_reachable_to_look(entity_id, current_place_id, self.game_state_controller)

    def _evaluate_rag_antennas(self, eval_query: str, ctrl: GameStateController, active_entity_id: Optional[str], active_entity_name: Optional[str]):
        return RagAntennaEvaluator.evaluate_antennas(eval_query, ctrl, self.embedding_engine, active_entity_id, active_entity_name)

    def _are_condition_groups_met(self, groups: List[Any], ctrl: GameStateController, eval_query: str = "", precomputed_scores: Optional[Dict[str, float]] = None) -> bool:
        return LoreConditionEvaluator.are_condition_groups_met(groups, ctrl, eval_query, precomputed_scores, self.embedding_engine)

    def _is_single_condition_met(self, c: Dict[str, Any], ctrl: GameStateController) -> bool:
        return LoreConditionEvaluator.is_single_condition_met(c, ctrl)

    def _apply_lore_effects(self, effects: List[Dict[str, Any]], ctrl: GameStateController, autonomous_push: List[Tuple[str, str]]) -> None:
        LoreEffectApplier.apply_effects(effects, ctrl, autonomous_push)

    def _has_effective_active_conditions(self, blk: Dict[str, Any]) -> bool:
        return LoreConditionEvaluator.has_effective_active_conditions(blk)

    def _has_effective_done_conditions(self, blk: Dict[str, Any]) -> bool:
        return LoreConditionEvaluator.has_effective_done_conditions(blk)

    def _block_affects_entity(self, blk: Dict[str, Any], entity_id: Optional[str]) -> bool:
        return LoreStateMachine.block_affects_entity(blk, entity_id)
