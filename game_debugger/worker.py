from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from domains.projections import ActionCommandProjection, TurnResultProjection


class TurnWorker(QThread):
    """
    Hilo de trabajo para ejecutar los turnos del juego de forma asíncrona,
    evitando que la interfaz gráfica principal (GUI) se congele durante
    las llamadas al modelo de lenguaje (LLM).
    """
    finished_turn = Signal(object)

    def __init__(
        self,
        session: Any = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        player_input: str = "",
        # Compatibilidad con llamadas heredadas (game_engine, dm, action_cmd, player_input):
        game_engine: Optional[Any] = None,
        dm: Optional[Any] = None,
        action_cmd: Optional[ActionCommandProjection] = None,
    ):
        super().__init__()
        self.session = session
        self.action = action
        self.target = target
        self.player_input = player_input
        self.game_engine = game_engine
        self.dm = dm
        self.action_cmd = action_cmd

        from engines.session import AdventureSession

        if (
            isinstance(target, ActionCommandProjection)
            or (target is not None and not isinstance(target, str) and hasattr(target, "action") and hasattr(target, "target"))
        ):
            # Firma heredada posicional: TurnWorker(game_engine, dm, action_cmd, player_input)
            self.game_engine = session
            self.dm = action
            self.action_cmd = target
            self.session = None
            self.action = getattr(target, "action", "")
            self.target = getattr(target, "target", "")
        elif isinstance(session, AdventureSession):
            self.session = session
            self.game_engine = None
        elif game_engine is not None:
            self.game_engine = game_engine
            self.session = None
        else:
            self.session = session

        if self.action_cmd is not None:
            if self.action is None:
                self.action = getattr(self.action_cmd, "action", "")
            if self.target is None:
                self.target = getattr(self.action_cmd, "target", "")

    def run(self):
        try:
            if self.session is not None:
                if self.player_input and not self.action:
                    turn_output = self.session.send_message(self.player_input)
                elif self.action and self.target:
                    turn_output = self.session.execute_action(self.action, self.target)
                elif self.player_input:
                    turn_output = self.session.send_message(self.player_input)
                else:
                    turn_output = self.session.execute_action(self.action or "LOOK", self.target or "")
            elif self.game_engine is not None:
                cmd = self.action_cmd or ActionCommandProjection(action=self.action or "LOOK", target=self.target or "")
                turn_output = self.game_engine.execute_turn(
                    cmd,
                    player_input=self.player_input,
                    dm=self.dm,
                )
            else:
                raise ValueError("TurnWorker requiere una AdventureSession o GameEngine válido.")

            self.finished_turn.emit(turn_output)
        except Exception as e:
            # Emitir un TurnResultProjection de error en caso de fallo
            err_output = TurnResultProjection(
                author="SYSTEM",
                msg=f"Error al procesar el turno: {str(e)}"
            )
            self.finished_turn.emit(err_output)

