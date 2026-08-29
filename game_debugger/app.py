import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QLabel, QSplitter
)
from PySide6.QtCore import Qt

from game_engine.engine import GameEngine
from transformer_engine import DungeonMaster
from game_debugger.views.chat_tab import ChatTab
from game_debugger.views.inspector import GameStateInspector
from game_debugger.worker import TurnWorker

class GameDebuggerApp(QMainWindow):
    """
    Ventana principal del depurador gráfico de juego (DEBUG Mode).
    """

    def __init__(self, game_engine: GameEngine, dm: DungeonMaster):
        super().__init__()
        self.setWindowTitle("Depurador de Juego - AAdventure")
        self.resize(1100, 750)

        self.engine = game_engine
        self.dm = dm
        self.worker = None

        # Widget central divisor
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # -------------------------------------------------------------
        # PANEL IZQUIERDO: Pestañas de depuración y juego
        # -------------------------------------------------------------
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # Pestaña 1: Juego
        self.chat_tab = ChatTab(self)
        self.chat_tab.send_input.connect(self.on_player_action)
        self.tab_widget.addTab(self.chat_tab, "Juego")

        # Pestaña 2: Prompt
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setReadOnly(True)
        self.prompt_edit.setPlaceholderText("Aquí se mostrará el prompt enviado al LLM en cada interacción...")
        self.tab_widget.addTab(self.prompt_edit, "Prompt")

        # Pestaña 3: Response (Raw + Structured side by side)
        response_tab = QWidget()
        res_layout = QVBoxLayout(response_tab)
        res_splitter = QSplitter(Qt.Horizontal)
        res_layout.addWidget(res_splitter)
        
        self.raw_response_edit = QTextEdit()
        self.raw_response_edit.setReadOnly(True)
        self.raw_response_edit.setPlaceholderText("Respuesta cruda (Raw) del modelo...")
        res_splitter.addWidget(self.raw_response_edit)

        self.structured_response_edit = QTextEdit()
        self.structured_response_edit.setReadOnly(True)
        self.structured_response_edit.setPlaceholderText("Estructura JSON mapeada del step...")
        res_splitter.addWidget(self.structured_response_edit)
        
        self.tab_widget.addTab(response_tab, "Response")

        # Pestaña 4: Result
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("Resultado de validaciones y ejecución del motor...")
        self.tab_widget.addTab(self.result_edit, "Result")

        # -------------------------------------------------------------
        # PANEL DERECHO: Inspector de estado en tiempo real
        # -------------------------------------------------------------
        self.inspector = GameStateInspector(self)
        splitter.addWidget(self.inspector)

        # Dimensionar el divisor (70% paneles de juego, 30% inspector)
        splitter.setSizes([750, 350])

        # Inicializar UI
        self.init_game_ui()

    def init_game_ui(self):
        """
        Carga el estado inicial del juego en la UI al arrancar.
        """
        # Refrescar inspector con estado inicial
        self.refresh_inspector()
        
        # Mensaje de bienvenida
        self.chat_tab.append_message("Dungeon Master", "La aventura ha sido cargada correctamente. Escribe tu primera acción para iniciar la narración.")
        
        # Barra de estado inferior
        self.update_status_bar()

    def refresh_inspector(self):
        game_state = self.engine.game_state_controller.data
        formatted_time = self.engine.get_formatted_time()
        self.inspector.update_state(game_state, formatted_time)

    def update_status_bar(self):
        ui_state = self.engine.get_ui_state()
        status_text = (
            f"Jugador: {ui_state['player_name']} | "
            f"Localización: {ui_state['current_location']} | "
            f"Oro: {ui_state['gold']} | "
            f"Tiempo: {ui_state['formatted_time']} | "
            f"Modo: {ui_state['game_state']}"
        )
        self.statusBar().showMessage(status_text)

    def on_player_action(self, player_input: str):
        """
        Se ejecuta cuando el jugador envía una entrada a través del chat.
        Inicia el hilo asíncrono para ejecutar el turno.
        """
        # Desactivar inputs
        self.chat_tab.set_input_enabled(False)
        self.statusBar().showMessage("Procesando turno con el Dungeon Master (LLM)...")

        # Log del input del jugador en el chat
        self.chat_tab.append_message(self.engine.get_player_name(), player_input)

        # Crear y arrancar QThread
        self.worker = TurnWorker(self.engine, self.dm, player_input)
        self.worker.finished_turn.connect(self.on_turn_finished)
        self.worker.start()

    def on_turn_finished(self, turn_output):
        """
        Callback que recibe los resultados del QThread al finalizar la llamada al LLM.
        """
        # Rehabilitar inputs
        self.chat_tab.set_input_enabled(True)

        # Agregar respuesta del Dungeon Master al chat
        self.chat_tab.append_message(turn_output.author, turn_output.msg)

        if turn_output.info_msg:
            self.chat_tab.append_message("SYSTEM", turn_output.info_msg)

        # Actualizar pestañas de depuración
        self.prompt_edit.setPlainText(turn_output.debug_prompt or "No disponible")
        self.raw_response_edit.setPlainText(turn_output.debug_raw_response or "No disponible")
        self.structured_response_edit.setPlainText(turn_output.debug_structured_response or "No disponible")
        self.result_edit.setPlainText(turn_output.debug_engine_result or "No disponible")

        # Actualizar inspector y barra de estado
        self.refresh_inspector()
        self.update_status_bar()
