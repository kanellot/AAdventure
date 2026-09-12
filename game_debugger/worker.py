from typing import Optional
from PySide6.QtCore import QThread, Signal
from engines.game.engine import GameEngine, TurnOutput
from domains import ActionCommand
from engines.transformer import TransformerEngine

class TurnWorker(QThread):
    """
    Hilo de trabajo para ejecutar los turnos del juego de forma asíncrona,
    evitando que la interfaz gráfica principal (GUI) se congele durante
    las llamadas al modelo de lenguaje (LLM).
    """
    finished_turn = Signal(object)

    def __init__(
        self, 
        game_engine: GameEngine, 
        dm: TransformerEngine, 
        action_cmd: ActionCommand, 
        player_input: str = ""
    ):
        super().__init__()
        self.game_engine = game_engine
        self.dm = dm
        self.action_cmd = action_cmd
        self.player_input = player_input

    def run(self):
        try:
            # Ejecutar el turno de 1 solo paso usando el motor y LLM
            turn_output = self.game_engine.execute_turn(
                self.action_cmd, 
                player_input=self.player_input, 
                dm=self.dm
            )
            self.finished_turn.emit(turn_output)
        except Exception as e:
            # Emitir un TurnOutput de error en caso de fallo
            err_output = TurnOutput(
                author="SYSTEM",
                msg=f"Error al procesar el turno: {str(e)}"
            )
            self.finished_turn.emit(err_output)
