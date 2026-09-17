import os
from typing import Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from domains import ActionCommand
from domains.projections import TurnResultProjection
from engines import AdventureSession
from game_debugger.views.chat_tab import ChatTab
from game_debugger.views.entities_tab import EntitiesTreeWidget
from game_debugger.views.inspector import GameStateInspector
from game_debugger.views.lore_graph_tab import LoreGraphTab
from game_debugger.views.rag_tab import RagTab
from game_debugger.views.result_tab import ResultTab
from game_debugger.worker import TurnWorker


class GameDebuggerApp(QMainWindow):
    """Ventana principal del depurador gráfico de juego (DEBUG Mode).

    Interactúa exclusivamente con la fachada AdventureSession recibiendo y enviando DTOs.
    """

    def __init__(
        self,
        session_or_engine: Any = None,
        dm_or_aad: Any = None,
        aad_path: Optional[str] = None,
        session: Optional[AdventureSession] = None,
    ):
        super().__init__()
        self.setWindowTitle("Depurador de Juego - AAdventure")
        self.resize(1150, 780)

        # Resolver sesión (soporta tanto AdventureSession como firma heredada game_engine, dm)
        if session is not None:
            self.session = session
            self.aad_path = aad_path or session.aad_path
        elif isinstance(session_or_engine, AdventureSession):
            self.session = session_or_engine
            self.aad_path = aad_path or (dm_or_aad if isinstance(dm_or_aad, str) else None) or self.session.aad_path
        elif session_or_engine is not None:
            resolved_aad = aad_path or (dm_or_aad if isinstance(dm_or_aad, str) else None)
            self.session = AdventureSession(
                game_engine=session_or_engine,
                transformer_engine=dm_or_aad if hasattr(dm_or_aad, "llm_adapter") else None,
                aad_path=resolved_aad,
            )
            self.aad_path = resolved_aad
        else:
            raise ValueError("Se debe proporcionar una AdventureSession a GameDebuggerApp.")

        self.engine = self.session._engine
        self.dm = self.session._dm
        self.worker = None

        self._setup_menu()

        # Widget central divisor
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # -------------------------------------------------------------
        # PANEL IZQUIERDO: Pestañas Principales (Juego, RAG, Prompt, Result)
        # -------------------------------------------------------------
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # 1. Pestaña: Juego (Área interactiva de juego y narración)
        self.chat_tab = ChatTab(self)
        self.chat_tab.send_input.connect(self.on_player_action)
        self.chat_tab.send_action.connect(self.on_player_action_command)
        self.tab_widget.addTab(self.chat_tab, "Juego")

        # 2. Pestaña: RAG (Inspección semántica de prompt y antenas)
        self.rag_tab = RagTab(self)
        self.tab_widget.addTab(self.rag_tab, "RAG")

        # 3. Pestaña: LoreBlocks (Visor gráfico HSM y condiciones en tiempo real)
        self.lore_tab = LoreGraphTab(self)
        self.tab_widget.addTab(self.lore_tab, "LoreBlocks")

        # 4. Pestaña: Prompt (Prompt completo enviado al LLM)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setReadOnly(True)
        self.prompt_edit.setFontFamily("Consolas")
        self.prompt_edit.setPlaceholderText("Aquí se mostrará el prompt completo enviado al LLM en cada interacción...")
        self.tab_widget.addTab(self.prompt_edit, "Prompt")

        # 5. Pestaña: Result (Respuesta narrativa y resultado del motor de juego)
        self.result_tab = ResultTab(self)
        self.tab_widget.addTab(self.result_tab, "Result")

        # -------------------------------------------------------------
        # PANEL DERECHO: Pestañas de Navegación e Inspector
        # -------------------------------------------------------------
        self.right_tab_widget = QTabWidget()
        self.right_tab_widget.setUsesScrollButtons(False)
        self.right_tab_widget.setMinimumWidth(320)

        # Pestaña 1: Navigation (Árbol según fog_war, activa por defecto)
        self.navigation_tab = EntitiesTreeWidget(self, header_title="Navegación (Fog of War)")
        self.navigation_tab.entity_selected.connect(self.on_entity_selected_from_tree)
        self.right_tab_widget.addTab(self.navigation_tab, "Navigation")

        # Pestaña 2: Entities (Árbol completo sin niebla para depuración)
        self.entities_tab = EntitiesTreeWidget(self, header_title="Todas las Entidades (Debug)")
        self.entities_tab.entity_selected.connect(self.on_entity_selected_from_tree)
        self.right_tab_widget.addTab(self.entities_tab, "Entities")

        # Pestaña 3: Game state (Inspector de parámetros y estado)
        self.inspector = GameStateInspector(self)
        self.right_tab_widget.addTab(self.inspector, "Game state")

        # Navigation activa por defecto según especificación
        self.right_tab_widget.setCurrentIndex(0)

        splitter.addWidget(self.right_tab_widget)

        # Dimensionar divisor (68% izquierda, 32% derecha) y fijar proporciones estables
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([760, 360])

        # Inicializar UI y título
        self.init_game_ui()
        self.update_window_title()

    def _setup_menu(self):
        """Configura la barra de menú superior de la aplicación."""
        menubar = self.menuBar()
        archivo_menu = menubar.addMenu("Archivo")

        change_act = archivo_menu.addAction("Cambiar Aventura... (Selector)")
        change_act.setShortcut("Ctrl+O")
        change_act.triggered.connect(self.on_change_adventure_triggered)

        reload_act = archivo_menu.addAction("Reiniciar Aventura Actual")
        reload_act.setShortcut("Ctrl+R")
        reload_act.triggered.connect(self.on_reload_adventure_triggered)

        archivo_menu.addSeparator()

        exit_act = archivo_menu.addAction("Salir")
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)

    def update_window_title(self):
        """Actualiza el título de la ventana con el archivo y mundo cargados."""
        title = "Depurador de Juego - AAdventure"
        if self.aad_path:
            file_name = os.path.basename(self.aad_path)
            world_name = self.session.get_world_name()
            title = f"{title} [{file_name} - {world_name}]"
        self.setWindowTitle(title)

    def on_change_adventure_triggered(self):
        """Abre el diálogo selector de aventura para cargar otra aventura."""
        from adventure_selector import open_adventure_selector
        new_path = open_adventure_selector(parent=self, preselected_path=self.aad_path)
        if new_path:
            self.load_adventure(new_path)

    def on_reload_adventure_triggered(self):
        """Reinicia la aventura actual desde el archivo .aad."""
        target_path = self.aad_path
        if not target_path:
            from adventure_selector import get_default_adventure_path
            target_path = get_default_adventure_path()

        if target_path:
            self.load_adventure(target_path)
        else:
            QMessageBox.information(self, "Aviso", "No hay ninguna ruta de aventura registrada para reiniciar.")

    def load_adventure(self, aad_path: str):
        """Carga una nueva aventura .aad en caliente en el depurador."""
        if not os.path.exists(aad_path):
            QMessageBox.critical(self, "Error", f"No se encontró el archivo de aventura:\n{aad_path}")
            return

        try:
            self.statusBar().showMessage(f"Cargando aventura {os.path.basename(aad_path)}...")
            self.session.close()
            self.session = AdventureSession.start(aad_path)
            self.engine = self.session._engine
            self.dm = self.session._dm
            self.aad_path = aad_path

            # Limpiar contenido anterior de las pestañas
            self.chat_tab.chat_browser.clear()
            self.prompt_edit.clear()
            self.rag_tab.update_rag_evaluation(None)
            self.result_tab.update_result(None)

            # Inicializar UI con el nuevo estado del motor
            self.init_game_ui()
            self.update_window_title()
            self.statusBar().showMessage(f"Aventura '{os.path.basename(aad_path)}' cargada correctamente.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar la aventura:\n{e}")

    def on_main_tab_changed(self, index: int):
        """Mantiene la columna derecha siempre visible con ancho estable."""
        pass

    def init_game_ui(self):
        """Carga el estado inicial del juego en la UI al arrancar."""
        self.refresh_inspector()
        self.refresh_entities()
        self.refresh_lore_graph()

        # Cargar entidades objetivo en el selector del chat
        self.chat_tab.set_targets(self.session.get_all_target_names())
        ui_state = self.session.get_ui_state()
        self.chat_tab.set_game_state(
            ui_state.game_state,
            active_affinity=ui_state.active_npc_affinity,
            target_name=ui_state.player_target,
        )

        # Mensaje de bienvenida
        self.chat_tab.append_message(
            "Dungeon Master",
            "La aventura ha sido cargada correctamente. Usa los botones MOVE, LOOK o TALK para comenzar la depuración.",
        )

        self.update_status_bar()

    def refresh_inspector(self):
        """Actualiza el inspector de estado consumiendo el DTO GameStateProjection."""
        state_dto = self.session.get_game_state()
        self.inspector.update_state(state_dto)

    def refresh_entities(self):
        """Actualiza Navigation (con niebla) y Entities (completa) usando WorldHierarchyProjection."""
        nav_hierarchy = self.session.get_navigation_tree()
        self.navigation_tab.update_entities(nav_hierarchy)

        debug_hierarchy = self.session.get_entities_tree()
        self.entities_tab.update_entities(debug_hierarchy)

    def refresh_lore_graph(self):
        """Actualiza el visor gráfico de LoreBlocks consumiendo el DTO LoreGraphProjection."""
        lore_dto = self.session.get_lore_graph()
        self.lore_tab.update_lore_graph(lore_dto)

    def on_entity_selected_from_tree(self, entity_name: str):
        """Al seleccionar un lugar o NPC de cualquier árbol, lo establece como objetivo en el selector."""
        idx = self.chat_tab.target_combo.findText(entity_name)
        if idx >= 0:
            self.chat_tab.target_combo.setCurrentIndex(idx)
        else:
            self.chat_tab.target_combo.addItem(entity_name)
            self.chat_tab.target_combo.setCurrentText(entity_name)

    def update_status_bar(self):
        """Actualiza la barra de estado inferior consumiendo el DTO UIStateProjection."""
        ui_state = self.session.get_ui_state()
        mode_str = ui_state.game_state
        if ui_state.game_state == "TALK" and ui_state.player_target:
            if ui_state.active_npc_affinity is not None:
                mode_str = f"TALK ({ui_state.player_target} | Afinidad: {ui_state.active_npc_affinity:.2f})"
            else:
                mode_str = f"TALK ({ui_state.player_target})"

        status_text = (
            f"Jugador: {ui_state.player_name} | "
            f"Localización: {ui_state.current_location} | "
            f"Oro: {ui_state.gold} | "
            f"Tiempo: {ui_state.formatted_time} | "
            f"Modo: {mode_str}"
        )
        self.statusBar().showMessage(status_text)

    def on_player_action(self, player_input: str):
        """Se ejecuta cuando el jugador envía un mensaje de texto libre."""
        self.chat_tab.set_input_enabled(False)
        self.statusBar().showMessage("Enviando mensaje... (Llamando al LLM)")
        self.prompt_edit.setPlainText(
            f"Enviando interacción de diálogo...\nEsperando prompt y respuesta del LLM..."
        )
        self.rag_tab.update_rag_evaluation(None)
        self.result_tab.update_result(None)

        self.chat_tab.append_message(self.session.get_player_name(), player_input)

        # Iniciar hilo de trabajo asíncrono con send_message
        self.worker = TurnWorker(session=self.session, player_input=player_input)
        self.worker.finished_turn.connect(self.on_turn_finished)
        self.worker.start()

    def on_player_action_command(self, action_obj: ActionCommand, prompt_text: str):
        """Se ejecuta cuando el usuario pulsa un botón de acción directa (MOVE, LOOK, TALK)."""
        self.chat_tab.set_input_enabled(False)
        self.statusBar().showMessage(f"Ejecutando acción {action_obj.action} sobre {action_obj.target}... (Llamando al LLM)")
        self.prompt_edit.setPlainText(
            f"Generando interacción [{action_obj.action} -> {action_obj.target}]...\nEsperando prompt y respuesta del LLM..."
        )
        self.rag_tab.update_rag_evaluation(None)
        self.result_tab.update_result(None)

        # Formatear el log del comando en el chat
        cmd_text = f"[{action_obj.action} -> {action_obj.target}]"
        if prompt_text:
            cmd_text += f' "{prompt_text}"'
        self.chat_tab.append_message(self.session.get_player_name(), cmd_text)

        # Iniciar hilo de trabajo asíncrono con execute_action
        self.worker = TurnWorker(
            session=self.session,
            action=action_obj.action,
            target=action_obj.target,
            player_input=prompt_text,
        )
        self.worker.finished_turn.connect(self.on_turn_finished)
        self.worker.start()

    def on_turn_finished(self, turn_output: TurnResultProjection):
        """Callback que recibe el TurnResultProjection del QThread al finalizar."""
        ui_state = self.session.get_ui_state()
        self.chat_tab.set_game_state(
            ui_state.game_state,
            active_affinity=ui_state.active_npc_affinity,
            target_name=ui_state.player_target,
        )
        self.chat_tab.set_input_enabled(True)

        # Agregar respuesta del Dungeon Master o NPC al chat
        self.chat_tab.append_message(turn_output.author, turn_output.msg)
        if turn_output.info_msg:
            self.chat_tab.append_message("SYSTEM", turn_output.info_msg)

        # Actualizar pestañas del panel principal
        self.rag_tab.update_rag_evaluation(turn_output.rag_evaluation)
        self.prompt_edit.setPlainText(turn_output.debug_prompt or "No disponible")
        self.result_tab.update_result(turn_output)

        # Actualizar inspector, árboles de entidades, lore graph y barra de estado
        self.refresh_inspector()
        self.refresh_entities()
        self.refresh_lore_graph()
        self.update_status_bar()
