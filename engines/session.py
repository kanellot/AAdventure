"""Fachada pública y caja cerrada para el motor de AAdventure.

AdventureSession proporciona la única interfaz pública de alto nivel para interactuar
con las mecánicas de juego, el modelo de lenguaje (LLM) y la progresión de estado,
desacoplando completamente los clientes UI y depuradores de la lógica interna de engines.
"""

from __future__ import annotations
import os
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
    # ACCIONES E INTERACCIÓN DEFENSIVA
    # =========================================================================

    def execute_action(self, action: str, target: str) -> TurnResultProjection:
        """Ejecuta una acción directa del mundo (MOVE, LOOK, TALK).

        Si el jugador se encuentra en estado TALK y la UI dispara una acción MOVE,
        la conversación finaliza abruptamente (limpiando conversación activa y afinidad del NPC)
        y el estado cambia a MOVE, ejecutando el desplazamiento de forma limpia.
        """
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
            # Regla acordada: Salida abrupta de TALK si se emite MOVE
            current_ui_state = self.get_ui_state()
            interrupted_conversation = False

            if current_ui_state.game_state == "TALK" and act == "MOVE":
                # Finalización abrupta de la conversación
                self._engine.game_state_controller.update_state("EXPLORE")
                if hasattr(self._engine.game_state_controller.data, "state"):
                    self._engine.game_state_controller.data.state.player_target = ""
                    self._engine.game_state_controller.data.state.active_npc_affinity = None
                self._engine.game_state_controller.sync_active_npc_affinity()
                interrupted_conversation = True

            cmd = ActionCommandProjection(action=act, target=tgt)
            res = self._engine.execute_turn(cmd, dm=self._dm)

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
        """Envía un mensaje de texto libre en una interacción conversacional (TALK o LOOK).

        Si el jugador se encuentra en modo EXPLORE, no lanza excepción y devuelve un
        TurnResultProjection descriptivo indicando la discrepancia de estado.
        """
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

    def get_available_actions(self) -> AvailableActionsProjection:
        """Devuelve las opciones y acciones accesibles en el turno actual."""
        return self._engine.get_available_actions_projection()

    def get_game_state(self) -> GameStateProjection:
        """Devuelve una instantánea detallada del estado para depuración o inspección."""
        return self._engine.get_game_state_projection()

    def get_navigation_tree(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía de lugares descubiertos bajo la niebla de guerra."""
        return self._engine.get_navigation_hierarchy()

    def get_entities_tree(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía completa del mundo con fines de depuración."""
        return self._engine.get_entities_hierarchy()

    def get_lore_graph(self) -> LoreGraphProjection:
        """Devuelve el grafo de LoreBlocks y sus condiciones evaluadas."""
        return self._engine.get_lore_graph_projection()

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
            if hasattr(self._engine, "cleanup"):
                self._engine.cleanup()
            self._closed = True

    def __enter__(self) -> AdventureSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
