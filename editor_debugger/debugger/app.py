from __future__ import annotations
import os
from PySide6.QtCore import Qt, Signal
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

from domains.projections import ActionCommandProjection, TurnResultProjection, UIStateProjection
from engines import AdventureSession
from engines.game.engine import GameEngine
from editor_debugger.debugger.views.chat_tab import ChatTab
from editor_debugger.debugger.views.entities_tab import AllEntitiesTreeWidget, EntitiesTreeWidget, MapTreeWidget
from editor_debugger.debugger.views.inspector import GameStateHierarchicalTreeWidget, GameStateInspector, NotebookTreeWidget
from editor_debugger.debugger.views.lore_graph_tab import LoreGraphTab
from editor_debugger.debugger.views.rag_tab import RagTab
from editor_debugger.debugger.views.result_tab import ResultTab
from editor_debugger.debugger.qt_listener import QtEngineListener
from engines.events import ThinkingEvent


class GameDebuggerApp(QMainWindow):
    """Ventana principal del depurador gráfico de juego (DEBUG Mode).

    Interactúa con AdventureSession recibiendo y enviando DTOs y eventos,
    y consulta GameEngine directamente para introspección y proyecciones de estado.
    """

    adventure_state_changed = Signal(bool)

    def __init__(
        self,
        engine: Optional[GameEngine] = None,
        session: Optional[AdventureSession] = None,
        aad_path: Optional[str] = None,
        auto_start: bool = False,
    ):
        super().__init__()
        self.setWindowTitle("Depurador de Juego - AAdventure")
        self.resize(1150, 780)

        if engine is not None:
            self.engine = engine
            self.session = session or AdventureSession(game_engine=self.engine, aad_path=aad_path)
            self.aad_path = aad_path or self.session.aad_path
        elif session is not None:
            self.session = session
            self.engine = getattr(session, "_engine", None)
            if self.engine is None and aad_path:
                self.engine = GameEngine(aad_path=aad_path)
            self.aad_path = aad_path or session.aad_path
        elif aad_path is not None:
            self.engine = GameEngine(aad_path=aad_path)
            self.session = AdventureSession(game_engine=self.engine, aad_path=aad_path)
            self.aad_path = aad_path
        else:
            raise ValueError("Se debe proporcionar GameEngine, AdventureSession o aad_path a GameDebuggerApp.")

        # Conectar observador reactivo Qt (los slots se conectan aquí y se registra tras crear la UI)
        self.listener = QtEngineListener(self)
        self.listener.thinking_changed.connect(self.on_thinking_changed)
        self.listener.task_completed.connect(self.on_task_completed)
        self.listener.state_updated.connect(self.on_state_updated)
        self.listener.task_error.connect(self.on_task_error)

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
        self.right_tab_widget.setUsesScrollButtons(True)
        self.right_tab_widget.setMinimumWidth(300)

        # Pestaña 1: Map (Árbol según fog_war, activa por defecto)
        self.map_tab = MapTreeWidget(self, header_title="Mapa (Fog of War)")
        self.navigation_tab = self.map_tab  # Alias para compatibilidad
        self.map_tab.entity_selected.connect(self.on_entity_selected_from_tree)
        self.map_tab.action_requested.connect(self.on_tree_action_requested)
        self.right_tab_widget.addTab(self.map_tab, "Map")

        # Pestaña 2: Entities (Árbol completo sin niebla para depuración)
        self.entities_tab = AllEntitiesTreeWidget(self, header_title="Todas las Entidades (Debug)")
        self.entities_tab.entity_selected.connect(self.on_entity_selected_from_tree)
        self.entities_tab.action_requested.connect(self.on_tree_action_requested)
        self.right_tab_widget.addTab(self.entities_tab, "Entities")

        # Pestaña 3: Notebook (Misiones activas y completadas)
        self.notebook_tab = NotebookTreeWidget(self)
        self.right_tab_widget.addTab(self.notebook_tab, "Notebook")

        # Pestaña 4: Gamestate (Inspector interactivo del estado de juego)
        self.gamestate_tab = GameStateHierarchicalTreeWidget(self)
        self.inspector = self.gamestate_tab  # Alias para compatibilidad
        self.right_tab_widget.addTab(self.gamestate_tab, "Gamestate")

        # Map activa por defecto según especificación
        self.right_tab_widget.setCurrentIndex(0)

        splitter.addWidget(self.right_tab_widget)

        # Dimensionar divisor (68% izquierda, 32% derecha) y fijar proporciones estables
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([760, 360])

        # Inicializar UI y título
        self.update_window_title()

        if auto_start:
            self.init_game_ui()
            # Registrar el listener para recibir actualizaciones de eventos
            self.session.add_listener(self.listener)
            self.session.start()
            self.is_running: bool = True
        else:
            self.is_running: bool = False
            self.cleanup_ui(message=None)

    def _setup_menu(self):
        """Configura la barra de menú superior de la aplicación."""
        menubar = self.menuBar()
        archivo_menu = menubar.addMenu("Archivo")

        change_act = archivo_menu.addAction("Cambiar Aventura... (Selector)")
        change_act.setShortcut("Ctrl+O")
        change_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        change_act.triggered.connect(self.on_change_adventure_triggered)

        start_act = archivo_menu.addAction("▶ Iniciar Aventura")
        start_act.setShortcut("F5")
        start_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        start_act.triggered.connect(lambda: self.start_adventure())

        stop_act = archivo_menu.addAction("■ Detener Aventura")
        stop_act.setShortcut("Shift+F5")
        stop_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        stop_act.triggered.connect(self.stop_adventure)

        reload_act = archivo_menu.addAction("Reiniciar Aventura Actual")
        reload_act.setShortcut("Ctrl+R")
        reload_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        reload_act.triggered.connect(self.on_reload_adventure_triggered)

        archivo_menu.addSeparator()

        exit_act = archivo_menu.addAction("Salir")
        exit_act.setShortcut("Ctrl+Q")
        exit_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        exit_act.triggered.connect(self.close)

    def update_window_title(self):
        """Actualiza el título de la ventana con el archivo y mundo cargados."""
        title = "Depurador de Juego - AAdventure"
        if self.aad_path:
            file_name = os.path.basename(self.aad_path)
            try:
                world_name = self.engine.get_world_name() if (self.engine and hasattr(self.engine, "get_world_name")) else "--"
            except Exception:
                world_name = "--"
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
        self.start_adventure()

    def start_adventure(self, aad_path: Optional[str] = None):
        """Inicia o reinicia la aventura en el depurador ejecutando el Turno 0."""
        target_path = aad_path or self.aad_path
        if not target_path:
            from adventure_selector import get_default_adventure_path
            target_path = get_default_adventure_path()

        if not target_path or not os.path.exists(target_path):
            QMessageBox.critical(self, "Error", f"No se encontró el archivo de aventura:\n{target_path}")
            return

        try:
            self.statusBar().showMessage(f"Iniciando aventura {os.path.basename(target_path)}...")
            if self.session and not self.session.is_closed:
                self.session.close()

            self.engine = GameEngine(aad_path=target_path)
            self.session = AdventureSession(game_engine=self.engine, aad_path=target_path)
            self.aad_path = target_path

            # Limpiar contenido anterior de las pestañas
            self.chat_tab.chat_browser.clear()
            self.prompt_edit.clear()
            self.rag_tab.update_rag_evaluation(None)
            self.result_tab.update_result(None)

            # Inicializar UI con el nuevo estado del motor
            self.init_game_ui()
            self.chat_tab.set_input_enabled(True)
            self.session.add_listener(self.listener)
            self.session.start()
            self.update_window_title()
            self.is_running = True
            self.statusBar().showMessage(f"Aventura '{os.path.basename(target_path)}' iniciada correctamente.", 4000)
            self.adventure_state_changed.emit(True)
        except Exception as e:
            QMessageBox.critical(self, "Error al Iniciar", f"No se pudo iniciar la aventura:\n{e}")

    def cleanup_ui(self, message: Optional[str] = "■ Partida detenida por el usuario."):
        """Limpia completamente todas las pestañas, paneles e inspectores del depurador."""
        # 1. Pestaña Juego
        self.chat_tab.cleanup()
        if message:
            self.chat_tab.append_message("SYSTEM", message)

        # 2. Pestañas de diagnóstico (panel izquierdo)
        self.rag_tab.update_rag_evaluation(None)
        self.lore_tab.update_lore_graph(None)
        self.prompt_edit.clear()
        self.result_tab.update_result(None)

        # 3. Pestañas del inspector y navegación (panel derecho)
        self.map_tab.clear()
        self.entities_tab.clear()
        self.notebook_tab.clear()
        self.gamestate_tab.clear()

    def set_adventure_path(self, aad_path: str):
        """Actualiza la ruta de la aventura activa en el depurador, detiene la partida previa y queda en STOP."""
        if getattr(self, "is_running", False):
            self.stop_adventure()
        else:
            self.cleanup_ui(message=None)

        self.aad_path = aad_path
        if aad_path and os.path.exists(aad_path):
            try:
                self.engine = GameEngine(aad_path=aad_path)
                self.session = AdventureSession(game_engine=self.engine, aad_path=aad_path)
            except Exception:
                pass
        self.update_window_title()

    def stop_adventure(self):
        """Detiene la aventura en curso y limpia completamente la interfaz."""
        if not getattr(self, "is_running", False):
            return

        try:
            if self.session and not self.session.is_closed:
                self.session.close()
            self.is_running = False

            # Limpiar toda la UI del depurador
            self.cleanup_ui("■ Partida detenida por el usuario.")

            self.statusBar().showMessage("Aventura detenida.", 4000)
            self.adventure_state_changed.emit(False)
        except Exception as e:
            QMessageBox.warning(self, "Error al Detener", f"Error al detener la aventura:\n{e}")

    def load_adventure(self, aad_path: str):
        """Carga una nueva aventura .aad en caliente en el depurador e inicia la partida."""
        self.start_adventure(aad_path)

    def closeEvent(self, event):
        """Al cerrar el depurador, detiene la sesión de juego de forma limpia."""
        try:
            if self.session and not self.session.is_closed:
                self.session.close()
        except Exception:
            pass
        super().closeEvent(event)

    def on_main_tab_changed(self, index: int):
        """Mantiene la columna derecha siempre visible con ancho estable."""
        pass

    def init_game_ui(self):
        """Carga el estado inicial del juego en la UI al arrancar."""
        self.refresh_map()
        self.refresh_entities()
        self.refresh_notebook()
        self.refresh_inspector()
        self.refresh_lore_graph()

        # Cargar entidades objetivo en el selector del chat
        self.chat_tab.set_targets(self.engine.get_all_target_names())
        ui_state = self.engine.get_ui_state_projection()
        self.chat_tab.set_game_state(
            ui_state.game_state,
            active_affinity=ui_state.active_npc_affinity,
            target_name=ui_state.player_target,
        )
        self.chat_tab.update_header_info(
            formatted_time=ui_state.formatted_time,
            player_state=ui_state.game_state,
            location_name=ui_state.current_location,
        )

        # Mensaje de bienvenida
        self.chat_tab.append_message(
            "Dungeon Master",
            "La aventura ha sido cargada correctamente. Usa los botones MOVE, LOOK o TALK para comenzar la depuración.",
        )

        self.update_status_bar()

    def refresh_map(self):
        """Actualiza el visor del mapa con niebla de guerra y resalta el lugar actual."""
        world_map = self.engine.get_world_map_projection()
        curr_p = self.engine.game_state_controller.game_state.current_location
        self.map_tab.update_map(world_map, curr_p)

    def refresh_notebook(self):
        """Actualiza el visor del cuaderno de misiones (Notebook)."""
        nb = self.engine.get_notebook_projection()
        self.notebook_tab.update_notebook(nb)

    def refresh_inspector(self):
        """Actualiza el inspector de estado consumiendo el DTO GameStateProjection."""
        state_dto = self.engine.get_game_state_projection()
        self.inspector.update_state(state_dto)

    def refresh_entities(self):
        """Actualiza Entities (completa sin niebla) usando WorldHierarchyProjection."""
        debug_hierarchy = self.engine.get_entities_hierarchy()
        self.entities_tab.update_entities(debug_hierarchy)

    def refresh_lore_graph(self):
        """Actualiza el visor gráfico de LoreBlocks consumiendo el DTO LoreGraphProjection."""
        lore_dto = self.engine.get_lore_graph_projection()
        self.lore_tab.update_lore_graph(lore_dto)

    def on_tree_action_requested(self, action: str, target: str):
        """Ejecuta una acción directa contextual al hacer doble clic sobre un nodo del árbol."""
        self.on_entity_selected_from_tree(target)
        self.on_player_action_command(ActionCommandProjection(action=action, target=target), "")

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
        ui_state = self.engine.get_ui_state_projection()
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
        self.prompt_edit.setPlainText(
            f"Enviando interacción de diálogo...\nEsperando prompt y respuesta del LLM..."
        )
        self.rag_tab.update_rag_evaluation(None)
        self.result_tab.update_result(None)

        self.chat_tab.append_message(self.engine.get_player_name(), player_input)

        # Enviar vía asíncrona reactiva no bloqueante mediante método unificado post_action
        self.session.post_action(action="", target="", player_input=player_input)

    def on_player_action_command(self, action_obj: ActionCommandProjection, prompt_text: str):
        """Se ejecuta cuando el usuario pulsa un botón de acción directa (MOVE, LOOK, TALK)."""
        self.prompt_edit.setPlainText(
            f"Generando interacción [{action_obj.action} -> {action_obj.target}]...\nEsperando prompt y respuesta del LLM..."
        )
        self.rag_tab.update_rag_evaluation(None)
        self.result_tab.update_result(None)

        # Formatear el log del comando en el chat
        cmd_text = f"[{action_obj.action} -> {action_obj.target}]"
        if prompt_text:
            cmd_text += f' "{prompt_text}"'
        self.chat_tab.append_message(self.engine.get_player_name(), cmd_text)

        # Enviar vía asíncrona reactiva no bloqueante
        self.session.post_action(
            action=action_obj.action,
            target=action_obj.target,
            player_input=prompt_text,
        )

    # =========================================================================
    # SLOTS REACTIVOS DESPACHADOS POR QTENGINE LISTENER EN EL HILO DE UI
    # =========================================================================

    def on_thinking_changed(self, event_json: str):
        """Maneja el cambio de estado Thinking activando/deteniendo el spinner y bloqueando entradas."""
        event = ThinkingEvent.model_validate_json(event_json)
        self.chat_tab.set_thinking(event.is_thinking, event.message)
        if event.is_thinking:
            self.statusBar().showMessage(f"⏳ {event.message or 'Pensando...'}")
        else:
            self.update_status_bar()

    def on_task_completed(self, task_id: str, result_json: str):
        """Recibe el resultado completado en JSON desde el worker thread de la sesión."""
        turn_output = TurnResultProjection.model_validate_json(result_json)
        # Agregar respuesta del Dungeon Master o NPC al chat
        self.chat_tab.append_message(turn_output.output.author or "Dungeon Master", turn_output.output.msg)

        # Si hubo un popup modal directo en la proyección, mostrarlo en pantalla
        if turn_output.output.type == "popup" or turn_output.output.popup_message:
            title = turn_output.output.popup_title or "Aviso del Sistema"
            msg = turn_output.output.popup_message or turn_output.output.msg
            QMessageBox.information(self, title, msg)

        # Actualizar pestañas del panel principal
        dbg = turn_output.debug
        self.rag_tab.update_rag_evaluation(dbg.rag_evaluation if dbg else None)
        self.prompt_edit.setPlainText((dbg.prompt if dbg else None) or "No disponible")
        self.result_tab.update_result(turn_output)

        # Actualizar mapa y cuaderno con la proyección del turno
        if turn_output.map:
            curr_p = self.engine.game_state_controller.game_state.current_location
            self.map_tab.update_map(turn_output.map, curr_p)
        if turn_output.notebook:
            self.notebook_tab.update_notebook(turn_output.notebook)

    def on_state_updated(self, state_json: str):
        """Actualiza la interfaz consolidada con el nuevo estado tras mutaciones."""
        ui_state = UIStateProjection.model_validate_json(state_json)
        self.chat_tab.set_game_state(
            ui_state.game_state,
            active_affinity=ui_state.active_npc_affinity,
            target_name=ui_state.player_target,
        )
        self.chat_tab.update_header_info(
            formatted_time=ui_state.formatted_time,
            player_state=ui_state.game_state,
            location_name=ui_state.current_location,
        )
        self.chat_tab.set_targets(self.engine.get_all_target_names())
        self.refresh_map()
        self.refresh_entities()
        self.refresh_notebook()
        self.refresh_inspector()
        self.refresh_lore_graph()
        self.update_status_bar()

    def on_task_error(self, task_id: str, error_message: str, error_code: str):
        """Maneja errores recibidos del motor."""
        self.chat_tab.append_message("SYSTEM", f"Error [{error_code}]: {error_message}")
        self.update_status_bar()


    def closeEvent(self, event):
        """Asegura la liberación de recursos y detención limpia del worker thread."""
        if hasattr(self, "session") and self.session:
            self.session.close()
        event.accept()
