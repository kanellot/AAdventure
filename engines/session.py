"""Fachada pública y caja cerrada para el motor de AAdventure.

AdventureSession proporciona la única interfaz pública de alto nivel para interactuar
con las mecánicas de juego, el modelo de lenguaje (LLM) y la progresión de estado,
desacoplando completamente los clientes UI y depuradores de la lógica interna de engines.
"""

from __future__ import annotations
import os
import queue
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from domains.projections import (
    ActionCommandProjection,
    AvailableActionsProjection,
    GameStateProjection,
    LoreGraphProjection,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
)
from engines.embedding.base_backend import BaseEmbeddingBackend
from engines.embedding.factory import EmbeddingFactory
from engines.events import EngineEventListener, EngineTask, ThinkingEvent
from engines.game.engine import GameEngine
from engines.transformer.base_adapter import BaseLLMAdapter
from engines.transformer.engine import TransformerEngine
from engines.transformer.factory import create_llm_adapter
from engines.transformer.mock_adapter import MockLLMAdapter

DEFAULT_LLM_CONFIG = os.path.join("Resources", "system_data", "llm_config.json")


class AdventureSession:
    """Sesión activa de aventura.

    Actúa como fachada unificada y defensiva para clientes y herramientas externas.
    Encapsula GameEngine, TransformerEngine y LoreRouter como una caja cerrada.
    """

    def __init__(
        self,
        game_engine: GameEngine,
        transformer_engine: Optional[TransformerEngine] = None,
        aad_path: Optional[str] = None,
    ):
        self._engine = game_engine
        if transformer_engine is None:
            self._dm = TransformerEngine(MockLLMAdapter())
        else:
            self._dm = transformer_engine
        self._aad_path = aad_path
        self._closed = False

        # Cola de tareas reactiva y listeners observadores
        self._listeners: List[EngineEventListener] = []
        self._listeners_lock = threading.Lock()
        self._task_queue: queue.Queue[Optional[EngineTask]] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_lock = threading.Lock()
        self._start_worker()

    @classmethod
    def start(
        cls,
        aad_path: str,
        config_path: Optional[str] = None,
    ) -> AdventureSession:
        """Inicia una nueva sesión cargando la aventura desde el archivo .aad.

        Configura el adaptador LLM y el sistema de embeddings predeterminados.
        """
        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        engine = GameEngine(world_json_path=aad_path)
        cfg = config_path or DEFAULT_LLM_CONFIG
        try:
            adapter = create_llm_adapter(config_or_path=cfg)
            dm = TransformerEngine(llm_adapter=adapter)
        except Exception as e:
            # En caso de no poder conectar con LLM externo en start(), recurrir a mock
            dm = TransformerEngine(MockLLMAdapter())

        return cls(game_engine=engine, transformer_engine=dm, aad_path=aad_path)

    @classmethod
    def start_for_testing(
        cls,
        aad_path: str,
        llm_adapter: Optional[BaseLLMAdapter] = None,
        embedding_backend: Optional[BaseEmbeddingBackend] = None,
    ) -> AdventureSession:
        """Inicia una sesión de testing completamente desacoplada de llamadas remotas.

        Permite inyectar adaptadores LLM mock y backends de embeddings deterministas.
        """
        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        if embedding_backend is not None:
            EmbeddingFactory.set_backend(embedding_backend)
        else:
            from engines.embedding.mock_backend import MockEmbeddingBackend
            EmbeddingFactory.set_backend(MockEmbeddingBackend())

        engine = GameEngine(world_json_path=aad_path)
        adapter = llm_adapter or MockLLMAdapter()
        dm = TransformerEngine(llm_adapter=adapter)

        return cls(game_engine=engine, transformer_engine=dm, aad_path=aad_path)

    @property
    def is_closed(self) -> bool:
        """Indica si la sesión ha sido cerrada y sus recursos liberados."""
        return self._closed

    @property
    def aad_path(self) -> Optional[str]:
        """Ruta al paquete canónico .aad de la sesión activa."""
        return self._aad_path

    # =========================================================================
    # GESTIÓN DE LISTENERS Y EVENTOS REACTIVOS (MOTOR-UI)
    # =========================================================================

    def add_listener(self, listener: EngineEventListener) -> None:
        """Registra un observador para recibir eventos reactivos de ejecución y estado."""
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: EngineEventListener) -> None:
        """Elimina un observador registrado."""
        with self._listeners_lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_thinking(self, event: ThinkingEvent) -> None:
        event_json = event.model_dump_json()
        with self._listeners_lock:
            listeners = list(self._listeners)
        for l in listeners:
            try:
                l.on_thinking_changed(event_json)
            except Exception:
                pass

    def _notify_task_completed(self, task_id: str, result: TurnResultProjection) -> None:
        result_json = result.model_dump_json()
        with self._listeners_lock:
            listeners = list(self._listeners)
        for l in listeners:
            try:
                l.on_task_completed(task_id, result_json)
            except Exception:
                pass

    def _notify_state_updated(self, ui_state: UIStateProjection) -> None:
        state_json = ui_state.model_dump_json()
        with self._listeners_lock:
            listeners = list(self._listeners)
        for l in listeners:
            try:
                l.on_state_updated(state_json)
            except Exception:
                pass

    def _notify_error(self, task_id: str, error_message: str, error_code: str) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for l in listeners:
            try:
                l.on_error(task_id, error_message, error_code)
            except Exception:
                pass

    # =========================================================================
    # BUCLE ASÍNCRONO DEL WORKER THREAD
    # =========================================================================

    def _start_worker(self) -> None:
        with self._worker_lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="AdventureSessionWorker",
                    daemon=True,
                )
                self._worker_thread.start()

    def _worker_loop(self) -> None:
        while not self._closed:
            try:
                task = self._task_queue.get()
                if task is None:
                    self._task_queue.task_done()
                    break

                self._process_task(task)
                self._task_queue.task_done()
            except Exception:
                pass

    def _process_task(self, task: EngineTask) -> None:
        # 1. Notificar Thinking = True
        desc = f"Pensando... [{task.action} -> {task.target}]" if task.action else "Pensando respuesta..."
        event_start = ThinkingEvent(
            task_id=task.task_id,
            is_thinking=True,
            action=task.action,
            target=task.target,
            source=task.source,
            message=desc,
        )
        self._notify_thinking(event_start)

        self._engine.pending_autonomous_actions = []

        try:
            if task.player_input and not task.action:
                result = self._execute_send_message_core(task.player_input)
            elif task.action:
                result = self._execute_action_core(task.action, task.target, player_input=task.player_input)
            else:
                result = self._execute_send_message_core(task.player_input)

            ui_state = self.get_ui_state()

            # 2. Entregar resultado y estado actualizado
            self._notify_task_completed(task.task_id, result)
            self._notify_state_updated(ui_state)

            # 3. Capturar acciones autónomas desencadenadas por LoreBlocks
            auto_actions = list(getattr(self._engine, "pending_autonomous_actions", []))
            self._engine.pending_autonomous_actions = []

            # 4. Notificar Thinking = False para la tarea actual
            event_done = ThinkingEvent(
                task_id=task.task_id,
                is_thinking=False,
                action=task.action,
                target=task.target,
                source=task.source,
                message="",
            )
            self._notify_thinking(event_done)

            # 5. Si hay acciones autónomas, encolarlas de inmediato como turnos secundarios
            for auto in auto_actions:
                act_type = auto.get("action", "TALK")
                act_target = auto.get("target", "")
                auto_task = EngineTask(
                    task_id=f"lore_{uuid.uuid4().hex[:8]}",
                    action=act_type,
                    target=act_target,
                    player_input=auto.get("prompt", ""),
                    source="LORE",
                )
                self._task_queue.put(auto_task)

        except Exception as e:
            self._notify_error(task.task_id, str(e), type(e).__name__)
            event_err = ThinkingEvent(
                task_id=task.task_id,
                is_thinking=False,
                action=task.action,
                target=task.target,
                source=task.source,
                message=f"Error: {str(e)}",
            )
            self._notify_thinking(event_err)

    # =========================================================================
    # API ASÍNCRONA REACTIVA (NO BLOQUEANTE CON TASK_ID)
    # =========================================================================

    def post_action(self, action: str, target: str, player_input: str = "") -> str:
        """Encola una acción de forma asíncrona y no bloqueante.

        Retorna inmediatamente el task_id generado.
        Emite ThinkingEvent(is_thinking=True) para que la UI active su spinner de inmediato.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = EngineTask(
            task_id=task_id,
            action=(action or "").strip().upper(),
            target=(target or "").strip(),
            player_input=player_input or "",
            source="PLAYER",
        )

        event_queued = ThinkingEvent(
            task_id=task_id,
            is_thinking=True,
            action=task.action,
            target=task.target,
            source=task.source,
            message=f"Pensando... [{task.action} -> {task.target}]",
        )
        self._notify_thinking(event_queued)

        self._task_queue.put(task)
        return task_id

    def post_message(self, text: str) -> str:
        """Encola un mensaje de texto libre de forma asíncrona y no bloqueante.

        Retorna inmediatamente el task_id generado.
        Emite ThinkingEvent(is_thinking=True) para activar el spinner de inmediato.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = EngineTask(
            task_id=task_id,
            action="",
            target="",
            player_input=(text or "").strip(),
            source="PLAYER",
        )

        event_queued = ThinkingEvent(
            task_id=task_id,
            is_thinking=True,
            action="",
            target="",
            source="PLAYER",
            message="Pensando respuesta...",
        )
        self._notify_thinking(event_queued)

        self._task_queue.put(task)
        return task_id

    def wait_idle(self, timeout: Optional[float] = None) -> bool:
        """Espera a que todas las tareas encoladas y sus acciones autónomas terminen.

        Retorna True si todas las tareas finalizaron, o False si expiró el tiempo de espera.
        """
        with self._task_queue.all_tasks_done:
            if timeout is None:
                while self._task_queue.unfinished_tasks:
                    self._task_queue.all_tasks_done.wait()
                return True
            else:
                end_time = time.time() + timeout
                while self._task_queue.unfinished_tasks:
                    remaining = end_time - time.time()
                    if remaining <= 0.0:
                        return False
                    self._task_queue.all_tasks_done.wait(remaining)
                return True

    # =========================================================================
    # ACCIONES E INTERACCIÓN SÍNCRONA DIRECTA (TESTS Y SCRIPTS)
    # =========================================================================

    def execute_action(self, action: str, target: str) -> TurnResultProjection:
        """Ejecuta una acción directa del mundo (MOVE, LOOK, TALK) de forma síncrona."""
        task_id = f"sync_{uuid.uuid4().hex[:8]}"
        self._notify_thinking(ThinkingEvent(
            task_id=task_id, is_thinking=True, action=action, target=target, message="Pensando..."
        ))
        try:
            res = self._execute_action_core(action, target)
            self._notify_task_completed(task_id, res)
            self._notify_state_updated(self.get_ui_state())

            # Drenar acciones autónomas de LoreBlocks si se hubieran producido
            auto_actions = list(getattr(self._engine, "pending_autonomous_actions", []))
            self._engine.pending_autonomous_actions = []
            for auto in auto_actions:
                act_type = auto.get("action", "TALK")
                act_target = auto.get("target", "")
                auto_task = EngineTask(
                    task_id=f"lore_{uuid.uuid4().hex[:8]}",
                    action=act_type,
                    target=act_target,
                    player_input=auto.get("prompt", ""),
                    source="LORE",
                )
                self._task_queue.put(auto_task)

            return res
        finally:
            self._notify_thinking(ThinkingEvent(
                task_id=task_id, is_thinking=False, action=action, target=target, message=""
            ))

    def _execute_action_core(self, action: str, target: str, player_input: str = "") -> TurnResultProjection:
        if self._closed:
            return TurnResultProjection(
                author="SYSTEM",
                msg="La sesión de aventura ha sido cerrada.",
                info_msg="Error: Sesión inactiva."
            )

        if not action or not isinstance(action, str):
            return TurnResultProjection(
                author="SYSTEM",
                msg="Acción no válida o vacía. Las acciones admitidas son MOVE, LOOK y TALK.",
                info_msg="Discrepancia de API: parámetro action inválido."
            )

        act = action.strip().upper()
        if act not in ("MOVE", "LOOK", "TALK"):
            return TurnResultProjection(
                author="SYSTEM",
                msg=f"Acción '{action}' no reconocida. Las acciones válidas son: MOVE, LOOK, TALK.",
                info_msg="Discrepancia de API: acción desconocida."
            )

        tgt = (target or "").strip()
        if not tgt:
            return TurnResultProjection(
                author="SYSTEM",
                msg=f"Debes especificar un objetivo válido para la acción {act}.",
                info_msg=f"Discrepancia de API: target vacío para {act}."
            )

        try:
            current_ui_state = self.get_ui_state()
            interrupted_conversation = False

            if current_ui_state.game_state == "TALK" and act == "MOVE":
                self._engine.game_state_controller.update_state("EXPLORE")
                if hasattr(self._engine.game_state_controller.data, "state"):
                    self._engine.game_state_controller.data.state.player_target = ""
                    self._engine.game_state_controller.data.state.active_npc_affinity = None
                self._engine.game_state_controller.sync_active_npc_affinity()
                interrupted_conversation = True

            cmd = ActionCommandProjection(action=act, target=tgt)
            res = self._engine.execute_turn(cmd, player_input=player_input, dm=self._dm)

            if interrupted_conversation:
                extra_info = "Has interrumpido la conversación abruptamente al desplazarte."
                res.info_msg = f"{extra_info} {res.info_msg or ''}".strip()

            return res
        except Exception as e:
            return TurnResultProjection(
                author="SYSTEM",
                msg=f"Error al procesar la acción {act} sobre '{tgt}': {str(e)}",
                info_msg=f"Excepción interna capturada: {type(e).__name__}"
            )

    def send_message(self, text: str) -> TurnResultProjection:
        """Envía un mensaje de texto libre en una interacción conversacional (TALK o LOOK) de forma síncrona."""
        task_id = f"sync_{uuid.uuid4().hex[:8]}"
        self._notify_thinking(ThinkingEvent(
            task_id=task_id, is_thinking=True, action="", target="", message="Pensando respuesta..."
        ))
        try:
            res = self._execute_send_message_core(text)
            self._notify_task_completed(task_id, res)
            self._notify_state_updated(self.get_ui_state())

            # Drenar acciones autónomas de LoreBlocks si se hubieran producido
            auto_actions = list(getattr(self._engine, "pending_autonomous_actions", []))
            self._engine.pending_autonomous_actions = []
            for auto in auto_actions:
                act_type = auto.get("action", "TALK")
                act_target = auto.get("target", "")
                auto_task = EngineTask(
                    task_id=f"lore_{uuid.uuid4().hex[:8]}",
                    action=act_type,
                    target=act_target,
                    player_input=auto.get("prompt", ""),
                    source="LORE",
                )
                self._task_queue.put(auto_task)

            return res
        finally:
            self._notify_thinking(ThinkingEvent(
                task_id=task_id, is_thinking=False, action="", target="", message=""
            ))

    def _execute_send_message_core(self, text: str) -> TurnResultProjection:
        if self._closed:
            return TurnResultProjection(
                author="SYSTEM",
                msg="La sesión de aventura ha sido cerrada.",
                info_msg="Error: Sesión inactiva."
            )

        clean_text = (text or "").strip()
        if not clean_text:
            return TurnResultProjection(
                author="SYSTEM",
                msg="El mensaje enviado no puede estar vacío.",
                info_msg="Discrepancia de API: mensaje vacío."
            )

        ui_state = self.get_ui_state()
        curr_state = ui_state.game_state

        if curr_state == "EXPLORE":
            return TurnResultProjection(
                author="SYSTEM",
                msg="No puedes enviar mensajes de texto libre en modo EXPLORE. Elige una acción (MOVE, TALK, LOOK).",
                info_msg="Discrepancia de estado: modo de juego EXPLORE no admite texto libre."
            )

        target = ui_state.player_target or ""
        act = "TALK" if curr_state == "TALK" else "LOOK"

        try:
            cmd = ActionCommandProjection(action=act, target=target)
            return self._engine.execute_turn(cmd, player_input=clean_text, dm=self._dm)
        except Exception as e:
            return TurnResultProjection(
                author="SYSTEM",
                msg=f"Error al procesar el mensaje: {str(e)}",
                info_msg=f"Excepción interna capturada: {type(e).__name__}"
            )

    # =========================================================================
    # CONSULTAS Y PROYECCIONES DTO PARA UI / CLIENTES
    # =========================================================================

    def get_ui_state(self) -> UIStateProjection:
        """Devuelve el estado consolidado de la interfaz (HUD)."""
        return self._engine.get_ui_state_projection()

    def get_ui_state_json(self) -> str:
        """Devuelve el estado consolidado de la interfaz como cadena JSON."""
        return self.get_ui_state().model_dump_json()

    def get_available_actions(self) -> AvailableActionsProjection:
        """Devuelve las opciones y acciones accesibles en el turno actual."""
        return self._engine.get_available_actions_projection()

    def get_available_actions_json(self) -> str:
        """Devuelve las opciones accesibles como cadena JSON."""
        return self.get_available_actions().model_dump_json()

    def get_game_state(self) -> GameStateProjection:
        """Devuelve una instantánea detallada del estado para depuración o inspección."""
        return self._engine.get_game_state_projection()

    def get_game_state_json(self) -> str:
        """Devuelve la instantánea detallada del estado como cadena JSON."""
        return self.get_game_state().model_dump_json()

    def get_navigation_tree(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía de lugares descubiertos bajo la niebla de guerra."""
        return self._engine.get_navigation_hierarchy()

    def get_navigation_tree_json(self) -> str:
        """Devuelve la jerarquía bajo niebla de guerra como cadena JSON."""
        return self.get_navigation_tree().model_dump_json()

    def get_entities_tree(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía completa del mundo con fines de depuración."""
        return self._engine.get_entities_hierarchy()

    def get_entities_tree_json(self) -> str:
        """Devuelve la jerarquía completa del mundo como cadena JSON."""
        return self.get_entities_tree().model_dump_json()

    def get_lore_graph(self) -> LoreGraphProjection:
        """Devuelve el grafo de LoreBlocks y sus condiciones evaluadas."""
        return self._engine.get_lore_graph_projection()

    def get_lore_graph_json(self) -> str:
        """Devuelve el grafo de LoreBlocks como cadena JSON."""
        return self.get_lore_graph().model_dump_json()

    def get_player_name(self) -> str:
        """Devuelve el nombre del personaje jugador."""
        return self._engine.get_player_name()

    def get_world_name(self) -> str:
        """Devuelve el nombre del mundo de la aventura."""
        if hasattr(self._engine, "world_state") and hasattr(self._engine.world_state, "world"):
            return getattr(self._engine.world_state.world, "name", "") or "Aventura"
        return "Aventura"

    def get_all_target_names(self) -> List[str]:
        """Devuelve los nombres de todos los objetivos elegibles en el mundo."""
        return self._engine.get_all_target_names()

    # =========================================================================
    # PERSISTENCIA Y CICLO DE VIDA
    # =========================================================================

    def save(self, aad_path: Optional[str] = None) -> None:
        """Guarda el estado actual del juego en el paquete .aad."""
        target_path = aad_path or self._aad_path
        if not target_path:
            raise ValueError("No se ha especificado ninguna ruta de archivo .aad para guardar.")
        self._engine.save_state(target_path)

    def close(self) -> None:
        """Cierra la sesión y limpia los recursos temporales."""
        if not self._closed:
            self._closed = True
            try:
                self._task_queue.put(None)
                if self._worker_thread and self._worker_thread.is_alive():
                    self._worker_thread.join(timeout=1.0)
            except Exception:
                pass
            if hasattr(self._engine, "cleanup"):
                self._engine.cleanup()

    def __enter__(self) -> AdventureSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
