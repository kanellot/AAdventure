from PySide6.QtCore import QThread, Signal
from game_engine.engine import GameEngine, TurnOutput
from transformer_engine import DungeonMaster

class TurnWorker(QThread):
    """
    Hilo de trabajo para ejecutar los turnos del juego de forma asíncrona,
    evitando que la interfaz gráfica principal (GUI) se congele durante
    las llamadas al modelo de lenguaje (LLM).
    """
    finished_turn = Signal(TurnOutput)

    def __init__(self, game_engine: GameEngine, dm: DungeonMaster, player_input: str):
        super().__init__()
        self.game_engine = game_engine
        self.dm = dm
        self.player_input = player_input

    def run(self):
        try:
            # Ejecutar el turno usando el motor y LLM
            turn_output = self.game_engine.execute_turn(self.player_input, self.dm)
            self.finished_turn.emit(turn_output)
        except Exception as e:
            # Emitir un TurnOutput de error en caso de fallo
            err_output = TurnOutput(
                author="SYSTEM",
                msg=f"Error al procesar el turno: {str(e)}"
            )
            self.finished_turn.emit(err_output)
