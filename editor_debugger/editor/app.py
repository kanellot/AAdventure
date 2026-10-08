import os
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QMenu,
    QDialog,
    QSizePolicy,
)

from domains.lore import LoreBlock
from editor_debugger.editor.constants import TYPE_METADATA, get_allowed_child_types, init_preset_loreblock
from editor_debugger.editor.controller import EditorController
from editor_debugger.editor.views.dialogs import CreateLoreBlockDialog
from editor_debugger.editor.views.item_form import ItemForm
from editor_debugger.editor.views.location_form import LocationForm
from editor_debugger.editor.views.lore_block_form import LoreBlockForm
from editor_debugger.editor.views.npc_form import NPCForm
from editor_debugger.editor.views.place_form import PlaceForm
from editor_debugger.editor.views.player_form import PlayerForm
from editor_debugger.editor.views.story_config_form import StoryConfigForm
from editor_debugger.editor.views.world_form import WorldForm


class StoryEditorApp(QMainWindow):
    """
    Ventana principal del editor de historias AAdventure (IDE Narrativo).
    Permite construir y editar todas las entidades desacopladas con navegación jerárquica,
    sistema visual de emojis, cross-referencing y sin tablas pesadas.
    """

    story_loaded = Signal(str)
    story_saved = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Historias - AAdventure")
        self.resize(1120, 750)

        self.controller = EditorController()

        # Historial de navegación (Atrás / Adelante) basado en tuplas (item_type, entity_id)
        self.history: List[Tuple[str, str]] = []
        self.history_index: int = -1
        self.navigating_history: bool = False

        # 1. Configurar barra de menús
        self.setup_menu()

        # 2. Configurar el widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Panel Izquierdo: Buscador, Árbol y Botones de Creación
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # Barra de navegación del historial y buscador
        nav_box = QHBoxLayout()
        self.btn_back = QPushButton("⬅ Atrás")
        self.btn_back.setToolTip("Volver a la entidad visitada anteriormente")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self.navigate_back)

        self.btn_fwd = QPushButton("Adelante ➔")
        self.btn_fwd.setToolTip("Avanzar en el historial de navegación")
        self.btn_fwd.setEnabled(False)
        self.btn_fwd.clicked.connect(self.navigate_forward)

        nav_box.addWidget(self.btn_back)
        nav_box.addWidget(self.btn_fwd)
        left_layout.addLayout(nav_box)

        # Buscador en tiempo real
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Filtrar árbol de aventura...")
        self.search_edit.textChanged.connect(self.filter_tree)
        left_layout.addWidget(self.search_edit)

        # Árbol de navegación
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Estructura de la Aventura")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_tree_item_selected)
        left_layout.addWidget(self.tree)

        # Botones de creación rápida compactos con emoji y + verde
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        btn_layout.setContentsMargins(2, 4, 2, 4)

        btn_style = """
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #c5e1a5;
                border-radius: 4px;
                background-color: #f1f8e9;
                color: #2e7d32;
            }
            QPushButton:hover {
                background-color: #dcedc8;
                border-color: #43a047;
            }
            QPushButton:pressed {
                background-color: #c5e1a5;
            }
        """

        self.add_loc_btn = QPushButton("🗺️➕")
        self.add_loc_btn.setToolTip("Añadir Localización")
        self.add_loc_btn.setStyleSheet(btn_style)
        self.add_loc_btn.clicked.connect(self.on_add_location)

        self.add_place_btn = QPushButton("📍➕")
        self.add_place_btn.setToolTip("Añadir Lugar a Localización")
        self.add_place_btn.setStyleSheet(btn_style)
        self.add_place_btn.clicked.connect(self.on_add_place)

        self.add_npc_btn = QPushButton("👤➕")
        self.add_npc_btn.setToolTip("Añadir Personaje (NPC)")
        self.add_npc_btn.setStyleSheet(btn_style)
        self.add_npc_btn.clicked.connect(self.on_add_npc)

        self.add_item_btn = QPushButton("📦➕")
        self.add_item_btn.setToolTip("Añadir Ítem")
        self.add_item_btn.setStyleSheet(btn_style)
        self.add_item_btn.clicked.connect(self.on_add_item)

        self.add_lore_btn = QPushButton("📜➕")
        self.add_lore_btn.setToolTip("Añadir Bloque de Lore (HSM)")
        self.add_lore_btn.setStyleSheet(btn_style)
        self.add_lore_btn.clicked.connect(self.on_add_lore)

        for btn in [self.add_loc_btn, self.add_place_btn, self.add_npc_btn, self.add_item_btn, self.add_lore_btn]:
            btn.setFixedHeight(30)
            btn_layout.addWidget(btn)

        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_panel)

        # Panel Derecho: Formularios Dinámicos
        self.stacked_widget = QStackedWidget()

        self.world_form = WorldForm(self)
        self.location_form = LocationForm(self)
        self.place_form = PlaceForm(self.controller, self)
        self.npc_form = NPCForm(self.controller, self)
        self.player_form = PlayerForm(self)
        self.item_form = ItemForm(self.controller, self)
        self.lore_block_form = LoreBlockForm(self.controller, self)
        self.story_config_form = StoryConfigForm(self)

        # Conectar señales de cambio de nombre para actualizar el árbol en tiempo real
        self.world_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.location_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.place_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.npc_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.player_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.item_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)

        # Pantalla de bienvenida
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        self.welcome_label = QLabel(
            "Bienvenido al Editor de Historias de AAdventure\n\n"
            "Crea una nueva aventura o abre un archivo (.aad) para empezar."
        )
        self.welcome_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(self.welcome_label)

        self.stacked_widget.addWidget(self.world_form)  # 0
        self.stacked_widget.addWidget(self.location_form)  # 1
        self.stacked_widget.addWidget(self.place_form)  # 2
        self.stacked_widget.addWidget(self.npc_form)  # 3
        self.stacked_widget.addWidget(self.player_form)  # 4
        self.stacked_widget.addWidget(self.item_form)  # 5
        self.stacked_widget.addWidget(self.lore_block_form)  # 6
        self.stacked_widget.addWidget(self.story_config_form)  # 7
        self.stacked_widget.addWidget(self.welcome_widget)  # 8

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stacked_widget.setCurrentIndex(8)
        splitter.addWidget(self.stacked_widget)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 780])
        self.splitter = splitter

        default_aad = os.path.join("Resources", "adventure_data", "Adventure.aad")
        if os.path.exists(default_aad):
            try:
                self.controller.load_story(default_aad)
                self.refresh_tree()
                self.statusBar().showMessage(f"Aventura cargada: {default_aad}")
                self.story_loaded.emit(default_aad)
            except Exception:
                self.on_new_story()
        else:
            self.on_new_story()

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Archivo")

        new_action = QAction("Nueva Historia", self)
        new_action.triggered.connect(self.on_new_story)
        file_menu.addAction(new_action)

        open_action = QAction("Abrir Historia (.aad)...", self)
        open_action.triggered.connect(self.on_open_story)
        file_menu.addAction(open_action)

        save_action = QAction("Guardar", self)
        save_action.triggered.connect(self.on_save_story)
        file_menu.addAction(save_action)

        save_as_action = QAction("Guardar Como (.aad)...", self)
        save_as_action.triggered.connect(self.on_save_story_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # --- NAVEGACIÓN DE HISTORIAL ---

    def _get_item_key(self, item: Optional[QTreeWidgetItem]) -> Optional[Tuple[str, str]]:
        if not item:
            return None
        try:
            data = item.data(0, Qt.UserRole)
            if not data:
                return None
            item_type, obj = data
            if obj is None:
                return (item_type, item_type)
            obj_id = getattr(obj, "id", None) or getattr(obj, "name", None) or item_type
            return (item_type, str(obj_id))
        except Exception:
            return None

    def push_history(self, item: QTreeWidgetItem):
        if not item or self.navigating_history:
            return

        key = self._get_item_key(item)
        if not key:
            return

        if 0 <= self.history_index < len(self.history):
            if self.history[self.history_index] == key:
                return

        # Truncar historial si estábamos en medio
        self.history = self.history[:self.history_index + 1]
        self.history.append(key)
        self.history_index = len(self.history) - 1
        self.update_history_buttons()

    def navigate_back(self):
        while self.history_index > 0:
            self.history_index -= 1
            item_type, obj_id = self.history[self.history_index]
            self.navigating_history = True
            found = self.select_entity_by_id(item_type, obj_id)
            self.navigating_history = False
            self.update_history_buttons()
            if found:
                break

    def navigate_forward(self):
        while self.history_index < len(self.history) - 1:
            self.history_index += 1
            item_type, obj_id = self.history[self.history_index]
            self.navigating_history = True
            found = self.select_entity_by_id(item_type, obj_id)
            self.navigating_history = False
            self.update_history_buttons()
            if found:
                break

    def update_history_buttons(self):
        self.btn_back.setEnabled(self.history_index > 0)
        self.btn_fwd.setEnabled(self.history_index < len(self.history) - 1)

    def filter_tree(self, text: str):
        q = text.strip().lower()

        def filter_item(item: QTreeWidgetItem) -> bool:
            match = q in item.text(0).lower()
            child_matches = False
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    child_matches = True
            should_show = match or child_matches or not q
            item.setHidden(not should_show)
            if should_show and q:
                item.setExpanded(True)
            return should_show

        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))

    # --- RECONSTRUCCIÓN DEL ÁRBOL LATERAL ---

    def refresh_tree(self):
        current_key = self._get_item_key(self.tree.currentItem()) if self.tree.currentItem() else None
        self.tree.clear()
        if not self.controller.world:
            return

        # 1. Mundo (Localizaciones y Lugares)
        world_item = QTreeWidgetItem(self.tree)
        world_item.setText(0, f"🌍 Mundo: {self.controller.world.name}")
        world_item.setData(0, Qt.UserRole, ("world", self.controller.world))

        for loc in self.controller.get_locations():
            loc_item = QTreeWidgetItem(world_item)
            loc_item.setText(0, f"🗺️ {loc.name}")
            loc_item.setData(0, Qt.UserRole, ("location", loc))
            for place in loc.places:
                place_item = QTreeWidgetItem(loc_item)
                place_item.setText(0, f"📍 {place.name}")
                place_item.setData(0, Qt.UserRole, ("place", place))

        # 2. Personajes (NPCs)
        npcs = self.controller.get_npcs()
        npcs_group = QTreeWidgetItem(self.tree)
        npcs_group.setText(0, f"👥 Personajes (NPCs) ({len(npcs)})")
        npcs_group.setData(0, Qt.UserRole, ("npcs_group", None))
        for npc in npcs:
            npc_item = QTreeWidgetItem(npcs_group)
            init_str = f" [📍 {npc.initial_location}]" if npc.initial_location else " [Por LoreBlock]"
            npc_item.setText(0, f"👤 {npc.name}{init_str}")
            npc_item.setData(0, Qt.UserRole, ("npc", npc))

        # 3. Ítems (Nodos individuales)
        items = self.controller.items
        items_group = QTreeWidgetItem(self.tree)
        items_group.setText(0, f"📦 Ítems ({len(items)})")
        items_group.setData(0, Qt.UserRole, ("items_group", None))
        for it in items:
            item_node = QTreeWidgetItem(items_group)
            init_str = f" [📍 {it.initial_location}]" if it.initial_location else " [Por LoreBlock]"
            item_node.setText(0, f"📦 {it.name}{init_str}")
            item_node.setData(0, Qt.UserRole, ("item", it))

        # 4. Bloques de Lore (HSM Jerárquico)
        lore_blocks = self.controller.lore_blocks
        lore_group = QTreeWidgetItem(self.tree)
        lore_group.setText(0, f"📜 Bloques de Lore (HSM) ({len(lore_blocks)})")
        lore_group.setData(0, Qt.UserRole, ("lore_group", None))

        id_to_block = {b.id: b for b in lore_blocks}
        parent_to_children = {}
        for b in lore_blocks:
            p_id = getattr(b, "parent_id", None)
            if p_id and p_id in id_to_block:
                parent_to_children.setdefault(p_id, []).append(b)

        roots = [b for b in lore_blocks if not b.parent_id or b.parent_id not in id_to_block]

        TYPE_ICONS = {k: v["icon"] for k, v in TYPE_METADATA.items()}

        def add_lore_tree_item(parent_node, b: LoreBlock):
            item = QTreeWidgetItem(parent_node)
            has_children = b.id in parent_to_children and bool(parent_to_children[b.id])

            # Semáforo de estado
            st = b.state.lower() if isinstance(b.state, str) else b.state.value.lower()
            st_dot = "🟢" if st == "active" else ("🔵" if st == "done" else "⚪")

            # Icono según type
            type_val = getattr(b, "type", "Event") or "Event"
            icon = TYPE_ICONS.get(type_val, "⚡")
            folder_mark = " 📁" if has_children else ""
            title = b.title or b.name or b.id
            item.setText(0, f"{st_dot} {icon}{folder_mark} {title}")
            item.setData(0, Qt.UserRole, ("loreblock", b))

            for child in parent_to_children.get(b.id, []):
                add_lore_tree_item(item, child)

            return item

        for r in roots:
            add_lore_tree_item(lore_group, r)

        # 5. Jugador
        p_name = self.controller.player.name if self.controller.player else "Aventurero"
        p_init = self.controller.player.initial_location if self.controller.player else ""
        player_item = QTreeWidgetItem(self.tree)
        player_item.setText(0, f"🧙 Jugador: {p_name} (Inicio: {p_init or '¡SIN ASIGNAR!'})")
        player_item.setData(0, Qt.UserRole, ("player", self.controller.player))

        # 6. Configuración de Historia
        config_item = QTreeWidgetItem(self.tree)
        config_item.setText(0, "⚙️ Configuración de Historia")
        config_item.setData(0, Qt.UserRole, ("config", self.controller.story_config))

        self.tree.expandAll()

        # Restaurar selección si es posible
        if current_key:
            c_type, c_id = current_key
            self.select_entity_by_id(c_type, c_id)

    def select_entity_by_id(self, entity_type: str, entity_id: str) -> bool:
        def item_matches(item: QTreeWidgetItem) -> bool:
            try:
                data = item.data(0, Qt.UserRole)
                if not data:
                    return False
                d_type, d_obj = data
                if d_type != entity_type:
                    return False
                if d_obj is None:
                    return str(entity_id) == str(entity_type)
                obj_id = getattr(d_obj, "id", None) or getattr(d_obj, "name", None) or d_type
                return str(obj_id) == str(entity_id)
            except Exception:
                return False

        def find_and_select(parent_node: QTreeWidgetItem) -> bool:
            for i in range(parent_node.childCount()):
                child = parent_node.child(i)
                if item_matches(child):
                    self.tree.setCurrentItem(child)
                    return True
                if find_and_select(child):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if item_matches(top):
                self.tree.setCurrentItem(top)
                return True
            if find_and_select(top):
                return True
        return False

    def update_selected_tree_item_text(self, text: str):
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        item_type, obj = data
        if item_type == "world":
            item.setText(0, f"🌍 Mundo: {text}")
        elif item_type == "location":
            item.setText(0, f"🗺️ {text}")
        elif item_type == "place":
            item.setText(0, f"📍 {text}")
        elif item_type == "npc":
            p_init = f" [📍 {obj.initial_location}]" if getattr(obj, "initial_location", None) else " [Por LoreBlock]"
            item.setText(0, f"👤 {text}{p_init}")
        elif item_type == "item":
            p_init = f" [📍 {obj.initial_location}]" if getattr(obj, "initial_location", None) else " [Por LoreBlock]"
            item.setText(0, f"📦 {text}{p_init}")
        elif item_type == "loreblock":
            st = getattr(obj, "state", "unknown").lower()
            st_dot = "🟢" if st == "active" else ("🔵" if st == "done" else "⚪")
            icons = {"Chapter": "📖", "Quest": "⚔️", "Task": "📌", "Event": "⚡", "popup": "📢"}
            icon = icons.get(getattr(obj, "type", "Event"), "⚡")
            item.setText(0, f"{st_dot} {icon} {text}")
        elif item_type == "player":
            p_init = self.controller.player.initial_location if self.controller.player else ""
            item.setText(0, f"🧙 Jugador: {text} (Inicio: {p_init or '¡SIN ASIGNAR!'})")

    def on_tree_item_selected(self):
        item = self.tree.currentItem()
        if not item:
            if self.controller.world:
                self.welcome_label.setText(
                    "Selecciona una entidad en el árbol de aventura para ver y editar sus propiedades."
                )
            else:
                self.welcome_label.setText(
                    "Bienvenido al Editor de Historias de AAdventure\n\n"
                    "Crea una nueva aventura o abre un archivo (.aad) para empezar."
                )
            self.stacked_widget.setCurrentIndex(8)
            return

        self.push_history(item)

        data = item.data(0, Qt.UserRole)
        if not data:
            self.stacked_widget.setCurrentIndex(8)
            return

        item_type, obj = data
        if item_type == "world":
            self.world_form.set_world(obj)
            self.stacked_widget.setCurrentWidget(self.world_form)
        elif item_type == "location":
            self.location_form.set_location(obj)
            self.stacked_widget.setCurrentWidget(self.location_form)
        elif item_type == "place":
            all_places = self.controller.get_all_places()
            all_npcs = self.controller.get_npcs()
            self.place_form.set_place(obj, all_places, all_npcs)
            self.stacked_widget.setCurrentWidget(self.place_form)
        elif item_type == "npc":
            self.npc_form.set_npc(obj)
            self.stacked_widget.setCurrentWidget(self.npc_form)
        elif item_type == "item":
            self.item_form.set_item(obj)
            self.stacked_widget.setCurrentWidget(self.item_form)
        elif item_type == "loreblock":
            self.lore_block_form.set_lore_block(obj)
            self.stacked_widget.setCurrentWidget(self.lore_block_form)
        elif item_type == "player":
            all_places = self.controller.get_all_places()
            self.player_form.set_player(obj, all_places)
            self.stacked_widget.setCurrentWidget(self.player_form)
        elif item_type == "config":
            self.story_config_form.set_config(self.controller.story_config)
            self.stacked_widget.setCurrentWidget(self.story_config_form)
        elif item_type in ["npcs_group", "items_group", "lore_group"]:
            if item.childCount() > 0:
                self.tree.setCurrentItem(item.child(0))
            else:
                self.welcome_label.setText(f"No hay elementos en esta categoría ({item.text(0)}).")
                self.stacked_widget.setCurrentIndex(8)

    def navigate_to_lore_block(self, lb_id: str):
        """Salta directamente a la edición del LoreBlock seleccionado por ID."""
        self.select_entity_by_id("loreblock", lb_id)

    # --- ACCIONES DE ARCHIVO ---

    def load_story_file(self, file_path: str) -> bool:
        """Carga una aventura desde un archivo .aad y emite la señal story_loaded."""
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            self.controller.load_story(file_path)
            self.refresh_tree()
            self.stacked_widget.setCurrentIndex(8)
            self.history.clear()
            self.history_index = -1
            self.update_history_buttons()
            self.statusBar().showMessage(f"Historia cargada: {os.path.basename(file_path)}")
            self.story_loaded.emit(file_path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar la aventura:\n{e}")
            return False

    def on_new_story(self):
        self.controller.new_story()
        self.refresh_tree()
        self.stacked_widget.setCurrentIndex(8)
        self.history.clear()
        self.history_index = -1
        self.update_history_buttons()
        self.statusBar().showMessage("Nueva historia creada.")
        self.story_loaded.emit("")

    def on_open_story(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Aventura", "", "Archivos AAdventure (*.aad)"
        )
        if file_path:
            self.load_story_file(file_path)

    def has_unsaved_changes(self) -> bool:
        return getattr(self.controller, "is_dirty", False)

    def save_current_story(self) -> bool:
        """Guarda la historia activa en el editor delegando en on_save_story."""
        return self.on_save_story()

    def on_save_story(self) -> bool:
        valid, err = self.controller.validate_story()
        if not valid:
            QMessageBox.warning(self, "Validación de Aventura", err)
            return False

        if self.controller.current_file_path:
            try:
                self.controller.save_story(self.controller.current_file_path)
                self.refresh_tree()
                self.statusBar().showMessage(
                    f"Historia guardada en {os.path.basename(self.controller.current_file_path)}")
                self.story_saved.emit(self.controller.current_file_path)
                return True
            except ValueError as ve:
                QMessageBox.warning(self, "Validación de Aventura", str(ve))
                return False
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la aventura:\n{e}")
                return False
        else:
            return self.on_save_story_as()

    def on_save_story_as(self) -> bool:
        valid, err = self.controller.validate_story()
        if not valid:
            QMessageBox.warning(self, "Validación de Aventura", err)
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Aventura Como", "", "Archivos AAdventure (*.aad)"
        )
        if file_path:
            if not file_path.lower().endswith(".aad"):
                file_path += ".aad"
            try:
                self.controller.save_story(file_path)
                self.refresh_tree()
                self.statusBar().showMessage(f"Historia guardada como {os.path.basename(file_path)}")
                self.story_saved.emit(file_path)
                return True
            except ValueError as ve:
                QMessageBox.warning(self, "Validación de Aventura", str(ve))
                return False
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la aventura:\n{e}")
                return False
        return False

    # --- ACCIONES DE CREACIÓN DE ENTIDADES ---

    def on_add_location(self):
        if not self.controller.world:
            return
        name, ok = QInputDialog.getText(self, "Añadir Localización", "Nombre de la localización:")
        if ok and name.strip():
            new_loc = self.controller.add_location(name.strip(), "")
            self.refresh_tree()
            self.select_entity_by_id("location", new_loc.id)
            self.statusBar().showMessage(f"Localización '{name}' añadida.")

    def on_add_place(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Añadir Lugar", "Por favor, selecciona una Localización en el árbol primero.")
            return

        data = item.data(0, Qt.UserRole)
        if not data or data[0] != "location":
            QMessageBox.warning(self, "Añadir Lugar",
                                "Debes seleccionar un nodo de tipo Localización en el árbol para añadirle un lugar.")
            return

        location = data[1]
        name, ok = QInputDialog.getText(self, "Añadir Lugar", f"Nombre del lugar para {location.name}:")
        if ok and name.strip():
            new_place = self.controller.add_place(location.id, name.strip(), "")
            self.refresh_tree()
            if new_place:
                self.select_entity_by_id("place", new_place.id)
            self.statusBar().showMessage(f"Lugar '{name}' añadido a {location.name}.")

    def on_add_npc(self):
        name, ok = QInputDialog.getText(self, "Añadir NPC", "Nombre del personaje:")
        if ok and name.strip():
            new_npc = self.controller.add_npc(name.strip(), "")
            self.refresh_tree()
            self.select_entity_by_id("npc", new_npc.id)
            self.statusBar().showMessage(f"NPC '{name}' añadido.")

    def on_add_item(self):
        name, ok = QInputDialog.getText(self, "Añadir Ítem", "Nombre del ítem:")
        if ok and name.strip():
            new_item = self.controller.add_item(name.strip(), "")
            self.refresh_tree()
            self.select_entity_by_id("item", new_item.id)
            self.statusBar().showMessage(f"Ítem '{name}' añadido.")

    def on_add_lore(self, default_type: str = "Event", parent_id: Optional[str] = None):
        dialog = CreateLoreBlockDialog(
            default_type=default_type,
            parent_id=parent_id,
            all_blocks=self.controller.lore_blocks,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, type_val, pid = dialog.get_data()
            lb_id = f"lb_{len(self.controller.lore_blocks) + 1:02d}_{title.strip().lower().replace(' ', '_')}"
            new_lb = init_preset_loreblock(type_val, lb_id, title.strip(), pid)
            self.controller.add_lore_block(new_lb)
            self.refresh_tree()
            self.select_entity_by_id("loreblock", new_lb.id)
            self.statusBar().showMessage(f"LoreBlock '{title}' ({type_val}) añadido.")

    def on_add_place_to_loc(self, location):
        name, ok = QInputDialog.getText(self, "Añadir Lugar", f"Nombre del lugar para '{location.name}':")
        if ok and name.strip():
            new_place = self.controller.add_place(location.id, name.strip(), "")
            self.refresh_tree()
            if new_place:
                self.select_entity_by_id("place", new_place.id)
            self.statusBar().showMessage(f"Lugar '{name}' añadido a {location.name}.")

    def on_add_child_lore(self, parent_id: str, default_type: str = "Task"):
        self.on_add_lore(default_type=default_type, parent_id=parent_id)

    # --- MENÚ CONTEXTUAL DEL ÁRBOL ---

    def on_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type, obj = data
        menu = QMenu(self)

        if item_type == "world":
            act_add_loc = menu.addAction("🗺️➕ Añadir Localización...")
            act_add_loc.triggered.connect(self.on_add_location)

        elif item_type == "location":
            act_add_place = menu.addAction(f"📍➕ Añadir Lugar a '{obj.name}'...")
            act_add_place.triggered.connect(lambda: self.on_add_place_to_loc(obj))
            act_add_loc = menu.addAction("🗺️➕ Añadir otra Localización...")
            act_add_loc.triggered.connect(self.on_add_location)
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Eliminar Localización '{obj.name}'...")
            act_del.triggered.connect(lambda: self.delete_location(obj))

        elif item_type == "place":
            loc = self.controller.get_location_by_place_id(obj.id)
            if loc:
                act_add_place = menu.addAction(f"📍➕ Añadir otro Lugar en '{loc.name}'...")
                act_add_place.triggered.connect(lambda: self.on_add_place_to_loc(loc))
            else:
                act_add_place = menu.addAction("📍➕ Añadir Lugar...")
                act_add_place.triggered.connect(self.on_add_place)
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Eliminar Lugar '{obj.name}'...")
            act_del.triggered.connect(lambda: self.delete_place(obj))

        elif item_type == "npcs_group":
            act_add_npc = menu.addAction("👤➕ Añadir Personaje (NPC)...")
            act_add_npc.triggered.connect(self.on_add_npc)

        elif item_type == "npc":
            act_add_npc = menu.addAction("👤➕ Añadir otro Personaje (NPC)...")
            act_add_npc.triggered.connect(self.on_add_npc)
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Eliminar Personaje '{obj.name}'...")
            act_del.triggered.connect(lambda: self.delete_npc(obj))

        elif item_type == "items_group":
            act_add_item = menu.addAction("📦➕ Añadir Ítem...")
            act_add_item.triggered.connect(self.on_add_item)

        elif item_type == "item":
            act_add_item = menu.addAction("📦➕ Añadir otro Ítem...")
            act_add_item.triggered.connect(self.on_add_item)
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Eliminar Ítem '{obj.name}'...")
            act_del.triggered.connect(lambda: self.delete_item(obj))

        elif item_type == "lore_group":
            act_add_chapter = menu.addAction("📖➕ Añadir Capítulo (Chapter)...")
            act_add_chapter.triggered.connect(lambda: self.on_add_lore(default_type="Chapter"))
            act_add_popup = menu.addAction("📢➕ Añadir Aviso Modal (popup)...")
            act_add_popup.triggered.connect(lambda: self.on_add_lore(default_type="popup"))

        elif item_type == "loreblock":
            title = obj.title or obj.name or obj.id
            allowed = get_allowed_child_types(getattr(obj, "type", "Event"))
            if allowed:
                for c_type in allowed:
                    meta = TYPE_METADATA.get(c_type, {"icon": "🔹", "label": c_type})
                    icon = meta.get("icon", "🔹")
                    label = meta.get("label", c_type)
                    act = menu.addAction(f"{icon}➕ Añadir {label}...")
                    act.triggered.connect(lambda _, t=c_type: self.on_add_child_lore(obj.id, default_type=t))
                menu.addSeparator()

            act_add_chapter = menu.addAction("📖➕ Añadir nuevo Capítulo raíz...")
            act_add_chapter.triggered.connect(lambda: self.on_add_lore(default_type="Chapter"))
            act_add_popup = menu.addAction("📢➕ Añadir Aviso Modal (popup) raíz...")
            act_add_popup.triggered.connect(lambda: self.on_add_lore(default_type="popup"))
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Eliminar LoreBlock '{title}'...")
            act_del.triggered.connect(lambda: self.delete_lore_block(obj))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # --- ACCIONES DE ELIMINACIÓN ---

    def delete_location(self, loc):
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar la localización '{loc.name}' ({loc.id}) junto con todos sus lugares ({len(loc.places)})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.remove_location(loc.id)
            self.refresh_tree()
            if self.controller.world:
                self.select_entity_by_id("world",
                                         getattr(self.controller.world, "id", None) or self.controller.world.name)
            else:
                self.stacked_widget.setCurrentIndex(8)
            self.statusBar().showMessage(f"Localización '{loc.name}' eliminada.")

    def delete_place(self, place):
        parent_loc = self.controller.get_location_by_place_id(place.id)
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el lugar '{place.name}' ({place.id})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.remove_place(place.id)
            self.refresh_tree()
            selected = False
            if parent_loc:
                selected = self.select_entity_by_id("location", parent_loc.id)
            if not selected:
                all_places = self.controller.get_all_places()
                if all_places:
                    selected = self.select_entity_by_id("place", all_places[0].id)
                elif self.controller.world:
                    selected = self.select_entity_by_id("world", getattr(self.controller.world, "id",
                                                                         None) or self.controller.world.name)
            if not selected:
                self.stacked_widget.setCurrentIndex(8)
            self.statusBar().showMessage(f"Lugar '{place.name}' eliminado.")

    def delete_npc(self, npc):
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el personaje '{npc.name}' ({npc.id})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.remove_npc(npc.id)
            self.refresh_tree()
            npcs = self.controller.get_npcs()
            selected = False
            if npcs:
                selected = self.select_entity_by_id("npc", npcs[0].id)
            elif self.controller.world:
                selected = self.select_entity_by_id("world", getattr(self.controller.world, "id",
                                                                     None) or self.controller.world.name)
            if not selected:
                self.stacked_widget.setCurrentIndex(8)
            self.statusBar().showMessage(f"Personaje '{npc.name}' eliminado.")

    def delete_item(self, obj):
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el ítem '{obj.name}' ({obj.id})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.remove_item(obj.id)
            self.refresh_tree()
            items = self.controller.get_items()
            selected = False
            if items:
                selected = self.select_entity_by_id("item", items[0].id)
            elif self.controller.world:
                selected = self.select_entity_by_id("world", getattr(self.controller.world, "id",
                                                                     None) or self.controller.world.name)
            if not selected:
                self.stacked_widget.setCurrentIndex(8)
            self.statusBar().showMessage(f"Ítem '{obj.name}' eliminado.")

    def delete_lore_block(self, lb):
        title = lb.title or lb.name or lb.id
        parent_id = getattr(lb, "parent_id", None)
        children = [b for b in self.controller.lore_blocks if getattr(b, "parent_id", None) == lb.id]

        if children:
            res = QMessageBox.question(
                self,
                "Eliminar LoreBlock Contenedor",
                f"El bloque '{title}' contiene {len(children)} sub-bloque(s).\n\n"
                "¿Deseas eliminarlo JUNTO con todos sus sub-bloques en cascada?\n\n"
                "(Si eliges 'No', los sub-bloques se promoverán al nivel de su padre actual)",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if res == QMessageBox.Cancel:
                return
            elif res == QMessageBox.Yes:
                ids_to_del = {lb.id}
                changed = True
                while changed:
                    changed = False
                    for b in self.controller.lore_blocks:
                        if b.id not in ids_to_del and getattr(b, "parent_id", None) in ids_to_del:
                            ids_to_del.add(b.id)
                            changed = True
                for b_id in ids_to_del:
                    self.controller.remove_lore_block(b_id)
            else:
                for c in children:
                    c.parent_id = lb.parent_id
                self.controller.remove_lore_block(lb.id)
        else:
            confirm = QMessageBox.question(
                self,
                "Confirmar Eliminación",
                f"¿Estás seguro de eliminar el LoreBlock '{title}' ({lb.id})?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            self.controller.remove_lore_block(lb.id)

        self.refresh_tree()
        selected = False
        if parent_id and self.controller.get_lore_block_by_id(parent_id):
            selected = self.select_entity_by_id("loreblock", parent_id)
        if not selected:
            lore_blocks = self.controller.get_lore_blocks()
            if lore_blocks:
                selected = self.select_entity_by_id("loreblock", lore_blocks[0].id)
            elif self.controller.world:
                selected = self.select_entity_by_id("world", getattr(self.controller.world, "id",
                                                                     None) or self.controller.world.name)
        if not selected:
            self.stacked_widget.setCurrentIndex(8)
        self.statusBar().showMessage(f"LoreBlock '{title}' eliminado.")


def start_editor(*args, **kwargs):
    """Punto de entrada de conveniencia que delega en editor_debugger.editor.main.start_editor."""
    from editor_debugger.editor.main import start_editor as _start_editor
    return _start_editor(*args, **kwargs)
