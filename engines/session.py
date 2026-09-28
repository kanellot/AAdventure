"""Fachada pública y caja cerrada para el cliente de AAdventure.

AdventureSession proporciona la interfaz de alto nivel para interactuar con las
mecánicas de juego, desacoplando los clientes UI de los subsistemas internos.
"""

from __future__ import annotations
import os
import uuid
from typing import Optional

from domains.projections import (
    NotebookProjection,
    TurnOutput,
    TurnResultProjection,
)
from engines.events import EngineEventListener
from engines.game.engine import GameEngine


class AdventureSession:
    """Sesión activa de aventura para clientes finales.

    Expone un único método de entrada de datos (post_action) y opera de forma
    asíncrona y reactiva hacia observadores EngineEventListener.
    """

    def __init__(
        self,
        game_engine: GameEngine,
        aad_path: Optional[str] = None,
    ):
        self._engine: GameEngine = game_engine
        self.aad_path: Optional[str] = aad_path
        self.is_closed: bool = False

        # Iniciar worker reactivo en segundo plano
        self._engine.start()

    @classmethod
    def create(cls, aad_path: str) -> AdventureSession:
        """Crea e inicializa una nueva sesión cargando la aventura desde el archivo .aad."""
        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        engine = GameEngine(aad_path=aad_path)
        return cls(game_engine=engine, aad_path=aad_path)

    def start(self) -> str:
        """Inicia formalmente la partida (Turno 0), mostrando el texto inicial del Dungeon Master y lanzando popups si los hay."""
        return self._engine.enqueue_start_game()

    def add_listener(self, listener: EngineEventListener) -> None:
        """Registra un observador reactivo y emite el estado inicial (State-on-Connect)."""
        self._engine.add_listener(listener)
        if hasattr(listener, "on_state_updated"):
            try:
                initial_state_json = self._engine.get_ui_state_projection().model_dump_json()
                listener.on_state_updated(initial_state_json)
            except Exception:
                pass

    def remove_listener(self, listener: EngineEventListener) -> None:
        """Elimina un observador registrado."""
        self._engine.remove_listener(listener)

    def post_action(self, action: str = "", target: str = "", player_input: str = "") -> str:
        """Único método de entrada de datos: encola una acción o input enviado por el jugador."""
        if self.is_closed:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            res = TurnResultProjection(
                output=TurnOutput(author="SYSTEM", type="msg", msg="La sesión está cerrada."),
                map=self._engine.get_world_map_projection(),
                inventory=self._engine.get_inventory_projection(),
                notebook=NotebookProjection(),
            )
            for l in self._engine.listeners:
                if hasattr(l, "on_task_completed"):
                    l.on_task_completed(task_id, res.model_dump_json())
            return task_id
        return self._engine.enqueue_action(action=action, target=target, player_input=player_input)

    def wait_idle(self, timeout: Optional[float] = None) -> bool:
        """Bloquea hasta que todas las tareas encoladas en el worker hayan finalizado."""
        try:
            self._engine.task_queue.join()
            return True
        except Exception:
            return False

    def save(self, aad_path: Optional[str] = None) -> None:
        """Guarda el estado actual de la partida en el paquete .aad."""
        self._engine.game_state_controller.save(filepath=aad_path or "quicksave")

    def close(self) -> None:
        """Cierra la sesión y detiene el worker en segundo plano."""
        if not self.is_closed:
            self.is_closed = True
            self._engine.stop()

    def __enter__(self) -> AdventureSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
